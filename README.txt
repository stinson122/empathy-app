Run scrapers and display results:
python scraper/run_scrapers.py
cd frontend
npm start

Web Scraping Notes:
The data should be good enough to use for now (Use the combined_data...json files). Though, it can definitely still be cleaned/normalized if needed.
I probably need to fix pa this - Some posts and megathread comments have several products, and this is not currently separated yet.
HomePage.js and .css are temporary frontend files displaying the results of the combined scraped data from posts and megathreads. I'll still need them for testing for now, so don't change them.
The ones I put in products.txt are the ones that I found most commonly in the megathreads. I also tried to use different brands, para less ung potential for same results of different products. Theres 7 cleansers, 7 sunscreens.
Links currently don't always work. I'm not sure if they will be used but if they will, I can work on them.
There's almost no images from any of the scraped subreddit posts/comments, so it's probably better and more reliable to manually get the images from online stores.
I couldn't find any more properly formatted megathreads for cleansers & sunscreens with enough useful content. There's only 5 I used.
Data is mostly gathered from megathreads. There's very few posts that match the products.