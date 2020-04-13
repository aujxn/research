import pandas as pd
import numpy as np
import pickle
import random
import scipy.sparse
from itertools import combinations
from ast import literal_eval
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
from scipy.spatial.distance import cosine

import torch
import torch.nn as nn
import torch.optim as optim
from torch.autograd import Variable

ingredients_map = {}
ingredients = []
counts = []
recipes = []

def main():
    #load()

    co_occur = scipy.sparse.load_npz('co_occur.npz')
    u = np.load('u.npy')
    s = np.load('s.npy')
    vh = np.load('vh.npy')

    with open('recipe_list.pickle', 'rb') as handle:
        recipes = pickle.load(handle)
    with open('ingredients_list.pickle', 'rb') as handle:
        ingredients = pickle.load(handle)
    with open('ingredients_map.pickle', 'rb') as handle:
        ingredients_map = pickle.load(handle)

    num_ingredients = 8
    lr = 0.0002
    num_epochs = 50
    nz = 12
    image_size = 40

    dataset = []

    for recipe in recipes:
        if len(recipe) == num_ingredients:
            feature = []
            for ingredient in recipe:
                for value in u[ingredient]:
                    feature.append(value)
            dataset.append(feature)
    
    tensor = torch.tensor(dataset)
    dataloader = torch.utils.data.DataLoader(tensor, batch_size = 128, shuffle=True)
    device = torch.device("cpu")

    generator = Generator().to(device)
    print(generator)

    discriminator = Discriminator().to(device)
    print(discriminator)

    criterion = nn.BCELoss()
    optimizerD = optim.Adam(discriminator.parameters(), lr=lr, betas=(0.5, 0.999))
    optimizerG = optim.Adam(generator.parameters(), lr=lr, betas=(0.5, 0.999))

    iters = 0

    for epoch in range(num_epochs):
        for i, data in enumerate(dataloader, 0):
            # train discriminator on real recipe
            discriminator.zero_grad()
            #real_cpu = data[0].to(device)
            b_size = data.size(0)
            label = torch.full((b_size,), 1, device=device)
            output = discriminator(data)
            errD_real = criterion(output, label)
            errD_real.backward()
            D_x = output.mean().item()

            # train discriminator on fake recipe
            noise = torch.randn(b_size, 12, device=device)
            fake = generator(noise)
            label.fill_(0)
            output = discriminator(fake.detach())
            errD_fake = criterion(output, label)
            errD_fake.backward()
            D_G_z1 = output.mean().item()
            errD = errD_real + errD_fake
            optimizerD.step()

            # train generator
            generator.zero_grad()
            label.fill_(1)
            output = discriminator(fake)
            errG = criterion(output, label)
            errG.backward()
            D_G_z2 = output.mean().item()
            optimizerG.step()

            if i % 50 == 0:
                print('[%d/%d] [%d/%d]\t Loss_D: %.4f\t Loss_G: %.4f\t D(x):%.4f\t D(G(z)): %.4f / %.4f' % (epoch, num_epochs, i, len(dataset), errD.item(), errG.item(), D_x, D_G_z1, D_G_z2))
            iters += 1

    torch.save(generator.state_dict(), './generator_model_state')
    torch.save(discriminator.state_dict(), './discriminator_model_state')

    recipes = []
    result = generator(torch.randn(15, 12)).detach().numpy()

    for recipe in result:
        print('\n\n')
        recipe_ingredients = []
        for j in range(8):
            start = j * 5 
            ingredient = recipe[start:start+5]
            
            ingredient_id = 0
            max_similarity = 0

            for k, real_ingredient in enumerate(u):
                similarity = 1 - cosine(ingredient, real_ingredient)
                if similarity > max_similarity:
                    max_similarity = similarity
                    ingredient_id = k

            recipe_ingredients.append(ingredients[ingredient_id])
            print('%s --- %d' % (recipe_ingredients[-1], max_similarity))

        recipes.append(recipe_ingredients)





class Generator(nn.Module):
    def __init__(self):
        super(Generator, self).__init__()
        self.main = nn.Sequential(
            nn.Linear(12, 20),
            nn.BatchNorm1d(20),
            nn.ReLU(),
            nn.Linear(20, 30),
            nn.BatchNorm1d(30),
            nn.ReLU(),
            nn.Linear(30, 40),
            nn.Tanh()
        )

    def forward(self, input):
        return self.main(input)

class Discriminator(nn.Module):
    def __init__(self):
        super(Discriminator, self).__init__()
        self.main = nn.Sequential(
            nn.Linear(40, 20),
            nn.BatchNorm1d(20),
            nn.ReLU(),
            nn.Linear(20, 1),
            nn.Sigmoid()
        )

    def forward(self, input):
        return self.main(input)

def load():
    recipes = pd.read_csv('../food_com_data/RAW_recipes.csv', converters={'ingredients': literal_eval})

    ingredients_map = {}
    ingredients = []
    counts = []
    recipe_list = []
    id = 0

    for index, recipe in recipes.iterrows():
        recipe_ingredients = []
        for ingredient in recipe['ingredients']:
            if ingredient not in ingredients_map.keys():
                ingredients_map[ingredient] = id
                ingredients.append(ingredient)
                recipe_ingredients.append(id)
                counts.append(0)
                id += 1
            else:
                ingredient = ingredients_map[ingredient]
                counts[ingredient] += 1
                recipe_ingredients.append(ingredient)
        recipe_list.append(recipe_ingredients)

    k = len(ingredients)

    with open('ingredients_map.pickle', 'wb') as handle:
        pickle.dump(ingredients_map, handle, protocol=pickle.HIGHEST_PROTOCOL)

    with open('ingredients_list.pickle', 'wb') as handle:
        pickle.dump(ingredients, handle, protocol=pickle.HIGHEST_PROTOCOL)

    with open('recipe_list.pickle', 'wb') as handle:
        pickle.dump(recipe_list, handle, protocol=pickle.HIGHEST_PROTOCOL)

    co_occur = np.zeros((k, k))

    for index, recipe in recipes.iterrows():
        for pair in combinations(recipe['ingredients'], 2):
            first = ingredients_map[pair[0]]
            second = ingredients_map[pair[1]]
            co_occur[first][second] += 1
            co_occur[second][first] += 1

    co_occur = csr_matrix(co_occur)
    scipy.sparse.save_npz('co_occur.npz', co_occur)

    u, s, vh = svds(co_occur, k=5) 

    np.save('u', u, allow_pickle=True, fix_imports=True)
    np.save('s', s, allow_pickle=True, fix_imports=True)
    np.save('vh', vh, allow_pickle=True, fix_imports=True)


if __name__ == '__main__':
    main()
