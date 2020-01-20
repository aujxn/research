from recipe_scrapers import scrape_me
import sqlite3
import time
import random
from sqlite3 import Error

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(sqlite3.version)
    except Error as e:
        print(e)

    return conn

def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)

def create_recipes_table():
    database = "recipes.db"
    table = """CREATE TABLE IF NOT EXISTS all_recipes (
                    id integer PRIMARY KEY,
                    title text NOT NULL,
                    time text NOT NULL,
                    yields text NOT NULL,
                    ingredients text NOT NULL,
                    instructions text NOT NULL,
                    ratings text NOT NULL,
                    url_id text NOT NULL
                );"""
    conn = create_connection(database)
    if conn is not None:
        create_table(conn, table)
    else:
        print("failed to create table")

def get_new_recipe_ids(links, all_recipes):
    page_recipes = set()
    for link in links:
        href = link.get('href')
        if href.startswith('https://www.allrecipes.com/recipe/'):
            href = href.strip('https://www.allrecipes.com/recipe/')
            recipe_id = href.split('/')[0]
            page_recipes.add(recipe_id)

    return page_recipes - all_recipes

def scrape_recipe(scraper, recipe_id):
    ingredients = scraper.ingredients()
    ingredients = '|'.join(ingredients)
    return (
            scraper.title(),
            str(scraper.total_time()),
            scraper.yields(),
            ingredients,
            scraper.instructions(),
            str(scraper.ratings()),
            recipe_id
            )

def insert_recipe(conn, recipe):
    sql = ''' INSERT INTO all_recipes(title,time,yields,ingredients,instructions,ratings,url_id)
              VALUES(?,?,?,?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, recipe)
    return cur.lastrowid

def main():
    #create_recipes_table()
    conn = create_connection("recipes.db")
    scraper = scrape_me('https://www.allrecipes.com/')
    all_recipes = set()
    to_scrape = get_new_recipe_ids(scraper.links(), all_recipes)
    next_recipe = to_scrape.pop();
    all_recipes.add(next_recipe)
    done = False

    while not done:
        time.sleep(random.random() * 10.0)
        
        try:
            scraper = scrape_me('https://www.allrecipes.com/recipe/' + next_recipe)
            new_recipes = get_new_recipe_ids(scraper.links(), all_recipes)
            to_scrape = to_scrape | new_recipes

            recipe = scrape_recipe(scraper, next_recipe)
            print(recipe)
            insert_recipe(conn, recipe)
        except Exception as e:
            print(e)

        finally:
            if len(to_scrape) == 0:
                done = True
            else:
                next_recipe = to_scrape.pop()
                all_recipes.add(next_recipe)
                continue

if __name__ == '__main__':
    main()
