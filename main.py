import discord
from bs4 import BeautifulSoup as bs
import aiohttp
from PIL import Image
import os
from replit import db
from keep_alive import keep_alive
from documentation import documentation

class manga_scraper(discord.Client):
    async def on_ready(self):
        print(f'{self.user} operational')
    
    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content.startswith('=shut_down') and message.author.id == 277375456523714560:
            await message.channel.send('Shutting down.')
            exit()
        elif message.content.startswith('=hello'):
            await message.channel.send(f'Hiiii {message.author.display_name}!!')
        elif message.content.startswith('=check_manga'):
            if len(message.content) < 14:
                await download_chapter(message,db.keys())
            else:
                arguments = message.content.split(' ')
                titles_set = set(arguments[1:])
                invalid_titles, titles = await validate_titles(titles_set)
                if not invalid_titles == set([]):
                  await message.channel.send(f'{invalid_titles} not found in database.')
                await download_chapter(message,titles)
        elif message.content.startswith('=add_manga'):
            if len(message.content) > 10:
                arguments = message.content.split(message.content[10])
                await register_manga(arguments,message)
        elif message.content.startswith('=help'):
            await message.channel.send(documentation)
        elif message.content.startswith('=list_manga'):
            await message.channel.send('\n'.join(db.keys()))

async def download_chapter(message,key_list):
    #spoofed headers to avoid 403 Forbidden
    spoofed_user_agent_headers = {'User-Agent':'Chrome/23.0.1271.64'}

    #creating ClientSession and requesting chapter webpage
    async with aiohttp.ClientSession(headers=spoofed_user_agent_headers) as session:
        for arguments in await get_links(key_list):
            title, link, new_line = arguments
            try:
                chapter = await session.get(link)
            except:
                print('Unable to download html. 403 Forbidden likely.')
                continue

            soup, image_tags = await download_images1(chapter,session) #validates amount of images

            if str(chapter.url) != link or soup == None:
                await message.channel.send(f'No new chapter found for {title}.')
                continue
            else:
                await message.channel.send(f'Found new chapter for {title}. Downloading.')

            #creates images array for PIL.Image objects and name of pdf
            pdf_name = soup.h1.get_text()+'.pdf'
            images = []

            file_names = await download_images2(session,images,image_tags) #returns an array of file names
            await construct_pdf(images,pdf_name)
            await send_file(pdf_name,835133123155066920)
            db[title] = new_line
            await clear_working(file_names,pdf_name)

async def clear_working(image_names,pdf_name):
    for file in image_names:
        if os.path.exists(file):
            os.remove(file)
    if os.path.exists(pdf_name):
        os.remove(pdf_name)

async def construct_pdf(images,pdf_name):
    #unpacking images for readability
    first_page = images[0]
    pages = images[1:]

    #constructs pdf
    first_page.save(pdf_name,save_all=True,append_images=pages)

async def download_images1(response,session): #first part to validate new chapter
    soup = bs(await response.text(),'html.parser') #creates bs4.BeautifulSoup object
    image_tags = soup.find_all('img')
    if len(image_tags) < 10: #validation for amount of images
        return None, None
    else:
        return soup, image_tags #returns the results of some processing so it doesnt have to be repeated

async def download_images2(session,master_array,image_tags): #second part to download all images
    file_names = []
    title_tag = await find_title_tag(image_tags[4])
    for page in image_tags:              #finds all <img> tags and iterates through them
        page_url = page.get('src')                 #url to download image from
        file_name = page.get(title_tag)+'.png'     #constructs filename using title pulled from <img> tag
        pagesRequest = await session.get(page_url) #creates aiohttp response object
        contents = await pagesRequest.read()       #creates a variable to store the bytes downloaded
        with open(file_name,'wb') as page_file:    #creates a file with the 'title' of the <img> tag
            page_file.write(contents)              #writes the image bytes to the created file
        master_array.append(Image.open(file_name)) #saves Image object of page into array to construct pdf
        file_names.append(file_name)               #saves names of files to delete later
    return file_names

async def find_title_tag(page): #this lets the code know where the title is in the img tag
    if page.get('title') == None:
      return 'alt' #'alt' here is the only other alternative ive found, this'll need updating later
    else:
      return 'title'

async def send_file(filename,channelid):
    #sends chapter to channel
    manga_channel = client.get_channel(channelid)
    await manga_channel.send(file=discord.File(filename))

async def register_manga(arguments,message): #stores information about a manga in the database
    title = arguments[1]
    if not title in db.keys():
        db[title] = ' '.join(arguments[1:])
        await message.channel.send(f'{title} has been added to the database.')
    else:
        await message.channel.send(f'{title} is already in database')

async def get_links(key_list): ##returns a list of tuples (title,link,new_link)
    arguments = [] #create empty links array which will store tuples
    for title_key in key_list: #iterates through database
        line_info = db[title_key].split(' ') #creates array holding info of line
        title = line_info[0] #index 0 of the words stored in the db value is title of the manga
        link = ''.join(line_info[1:]) #index 1-3 is url, split to keep chapter no. separate
        line_info[2] = str(int(line_info[2]) + 1) #increments only chapter number          
        new_line = ' '.join(line_info) #constructs new db value using incremented chapter number
        arguments.append((title,link,new_line)) #constructs tuple and adds to array
    return arguments

async def validate_titles(titles_set):
    invalid_titles = set([])
    valid_titles = list(titles_set)
    for title in titles_set:
        if not title in db.keys():
            invalid_titles.add(title)
            valid_titles.remove(title)
    return invalid_titles,valid_titles

keep_alive()
client = manga_scraper()
TOKEN = os.environ['TOKEN']

client.run(TOKEN)

print('Shutting dow-')