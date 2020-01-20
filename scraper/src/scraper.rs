extern crate select;

use crate::models::NewRecipe;
use indexmap::set::IndexSet;
use regex::Regex;
use reqwest::blocking::get;
use select::document::Document;
use select::predicate::{Attr, Class, Name, Predicate};

pub fn get_links(html_text: &String) -> IndexSet<i32> {
    let link_regex = Regex::new(r"www.allrecipes.com/recipe/(?P<url_id>\d+)/").unwrap();
    let links = link_regex
        .captures_iter(html_text)
        .map(|cap| cap["url_id"].parse().unwrap())
        .collect();
    println!("{:?}", links);
    links
}

// Takes the allrecipes recipe number and returns the recipe
// data as well as all of the linked recipes found on the page.
pub fn scrape(url_id: i32) -> (NewRecipe, IndexSet<i32>) {
    let url = String::from("https://www.allrecipes.com/recipe/") + &url_id.to_string();
    let response = get(url.as_str()).unwrap();
    let html_text = response.text().unwrap();
    let links = get_links(&html_text);

    let document = Document::from(html_text.as_str());

    let title = document
        .find(Class("recipe-summary__h1"))
        .next()
        .unwrap()
        .text();
    println!("{:?}", title);

    let ingredients: Vec<_> = document
        .find(Class("checkList__line").descendant(Name("label")))
        .filter_map(|ingredient| ingredient.attr("title"))
        .collect();
    let ingredients = ingredients.join("|");
    println!("{:?}", ingredients);

    let time = document.find(Class("ready-in-time")).next().unwrap().text();
    let hours = Regex::new(r"(?P<hours>\d+) h").unwrap();
    let mins = Regex::new(r"(?P<mins>\d+) m").unwrap();
    let hours = match hours.captures(&time) {
        Some(cap) => cap.name("hours").unwrap().as_str().parse().unwrap(),
        None => 0,
    };
    let mins = match mins.captures(&time) {
        Some(cap) => cap.name("mins").unwrap().as_str().parse().unwrap(),
        None => 0,
    };
    let time = hours as f32 + mins as f32 / 60.0;
    println!("{:?}", time);

    let yields = document
        .find(Name("meta"))
        .find(|x| x.attr("id") == Some("metaRecipeServings"));
    let yields = yields.unwrap().attr("content").unwrap().parse().unwrap();
    println!("{:?}", yields);

    let mut agg_rating = document.find(Class("aggregate-rating").descendant(Name("meta")));
    let rating = agg_rating
        .next()
        .unwrap()
        .attr("content")
        .unwrap()
        .parse()
        .unwrap();
    let reviews: i32 = agg_rating
        .next()
        .unwrap()
        .attr("content")
        .unwrap()
        .parse()
        .unwrap();
    println!("{:?}", rating);
    println!("{:?}", reviews);

    let instructions = document
        .find(Class("recipe-directions__list--item"))
        .map(|x| {
            let mut x = x.text();
            let chop = x.find('\n').unwrap_or(x.len());
            x.drain(..chop).collect::<String>()
        })
        .collect::<Vec<_>>()
        .join("|");
    println!("{:?}", instructions);

    (
        NewRecipe {
            title,
            time,
            yields,
            ingredients,
            instructions,
            rating,
            reviews,
            url_id,
        },
        links,
    )
}
