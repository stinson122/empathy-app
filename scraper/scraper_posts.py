import os
import praw
import json
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse
import glob

# Initialize Reddit instance (using same credentials as scraper_megathread.py)
reddit = praw.Reddit(
    client_id="Wt3DQHzvtI4_poBQ58Rn2g",
    client_secret="ilhFDto6TafES55zhDrQPJnyJ28ZOw",
    password="Dlsugrad#12",
    user_agent="script:megathread_scraper:v1.0",
    username="Successful_Body674",
)

def parse_skin_type(text: str) -> List[str]:
    """Parse skin type from text, handling various separators."""
    if not text:
        return []
    
    skin_types = {
        'normal': 'Normal',
        'dry': 'Dry',
        'oily': 'Oily',
        'combi': 'Combination',
        'combination': 'Combination',
        'acne': 'Acne Prone',
        'sensitive': 'Sensitive'
    }
    
    # Clean and split the text
    text = text.lower().strip()
    separators = [',', '/', 'to', 'and']
    for sep in separators:
        text = text.replace(sep, '|')
    
    # Find matching skin types
    found_types = []
    for part in text.split('|'):
        part = part.strip()
        for key, value in skin_types.items():
            if key in part and value not in found_types:
                found_types.append(value)
    
    return found_types

def extract_product_info(text: str, product_name: str) -> Optional[Dict]:
    """
    Extract product information from submission text.
    Modified version of the function from scraper_megathread.py to work with submission text.
    """
    if not text:
        return None
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return None
    
    product_info = {
        'skin_type': [],
        'product_name': product_name,  # Use the provided product name
        'price_size': None,
        'effects': None,
        'status': None,
        'availability': None,
        'comment': '\n'.join(lines)
    }
    
    # Parse fields from the submission text
    current_field = None
    for line in lines:
        line_lower = line.lower()
        
        if 'skin type' in line_lower and ':' in line:
            current_field = 'skin_type'
            skin_type = line.split(':', 1)[1].strip()
            product_info['skin_type'] = parse_skin_type(skin_type)
        elif 'price' in line_lower and ':' in line:
            current_field = 'price_size'
            product_info['price_size'] = line.split(':', 1)[1].strip()
        elif any(effect_key in line_lower for effect_key in ['effect', 'experience', 'exp']) and ':' in line:
            current_field = 'effects'
            product_info['effects'] = line.split(':', 1)[1].strip()
        elif 'status' in line_lower and ':' in line:
            current_field = 'status'
            status = line.split(':', 1)[1].strip().upper()
            if 'HG' in status or 'HOLY GRAIL' in status:
                product_info['status'] = 'HG (Holy Grail)'
            elif 'WR' in status or 'WILL REPURCHASE' in status:
                additional_text = ''
                if '(' in status and ')' in status:
                    additional_text = ' ' + status[status.find('('):status.rfind(')')+1]
                product_info['status'] = f'WR (Will Repurchase{additional_text})'
            elif 'WNR' in status or 'WILL NOT REPURCHASE' in status or 'WON\'T REPURCHASE' in status:
                product_info['status'] = 'WNR (Will Not Repurchase)'
        elif 'where to buy' in line_lower and ':' in line:
            current_field = 'availability'
            product_info['availability'] = line.split(':', 1)[1].strip()
        elif current_field == 'effects' and product_info['effects']:
            product_info['effects'] = (product_info['effects'] + ' ' + line).strip()
        elif current_field == 'availability' and product_info['availability']:
            product_info['availability'] = (product_info['availability'] + ' ' + line).strip()
    
    return product_info

def is_spam_post(text: str) -> bool:
    """Check if a post is likely spam based on simple heuristics."""
    if not text:
        return False
        
    normalized = ' '.join(text.lower().split())
    
    # Check for URL patterns
    url_pattern = r'https?://\S+'
    urls = re.findall(url_pattern, normalized)
    
    # If there's a URL and the post is very short, it's likely spam
    if urls and len(normalized) < 100:
        return True
        
    # Check for common spam phrases
    spam_phrases = [
        'click here',
        'buy now',
        'promo code',
        'limited time',
        'affiliate',
        'shop now',
        'check out my',
        'discount code',
        'use code',
        'coupon code'
    ]
    
    if any(phrase in normalized for phrase in spam_phrases):
        if len(normalized) < 200 or len(normalized.split()) < 30:
            return True
            
    return False

def get_products_from_file(filename: str = "products.txt") -> List[str]:
    """Get list of products from a file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Warning: {filename} not found. No product filtering will be applied.")
        return []

def scrape_product_submissions(subreddit_name: str = "beautytalkph", limit_per_product: int = 10) -> Dict[str, List[Dict]]:
    """
    Scrape product-specific submissions from a subreddit.
    
    Args:
        subreddit_name: Name of the subreddit to scrape
        limit_per_product: Maximum number of submissions to process per product
        
    Returns:
        Dictionary with two keys:
        - 'high_confidence': List of product info dicts with high confidence matches
        - 'low_confidence': List of product info dicts with lower confidence matches
    """
    # Get list of target products
    target_products = get_products_from_file("products.txt")
    if not target_products:
        print("No target products found. Please create a products.txt file with one product per line.")
        return {'high_confidence': [], 'low_confidence': []}
    
    print(f"Looking for posts about {len(target_products)} products in r/{subreddit_name}...")
    
    results = {
        'high_confidence': [],
        'low_confidence': []
    }
    
    for product in target_products:
        print(f"Searching for posts about: {product}")
        
        try:
            # Search for submissions containing the product name
            for submission in reddit.subreddit(subreddit_name).search(f'title:{product}', limit=limit_per_product):
                if submission.selftext == '[removed]' or submission.selftext == '[deleted]':
                    continue
                    
                # Skip spam posts
                if is_spam_post(submission.selftext):
                    print(f"Skipping potential spam post: {submission.title[:50]}...")
                    continue
                
                # Extract product info from the submission
                product_info = extract_product_info(submission.selftext, product)
                if not product_info:
                    continue
                
                # Add submission metadata
                product_info.update({
                    'comment_id': submission.id,
                    'comment_score': submission.score,
                    'comment_created_utc': submission.created_utc,
                    'comment_author': str(submission.author) if submission.author else None,
                    'match_confidence': 1.0,  # High confidence since we searched by product name
                    'matched_product': product,
                    'post_title': submission.title,
                    'post_url': f"https://reddit.com{submission.permalink}"
                })
                
                # Add to results (all results are considered high confidence in this case)
                results['high_confidence'].append(product_info)
                
                # Get top comments from the submission
                submission.comments.replace_more(limit=5)  # Load more comments if needed
                for comment in submission.comments.list()[:10]:  # Get top 10 comments
                    if not comment.body or comment.body == '[deleted]' or comment.body == '[removed]':
                        continue
                        
                    # Skip short comments
                    if len(comment.body.strip()) < 20:
                        continue
                        
                    # Create a product info entry for the comment
                    comment_info = extract_product_info(comment.body, product)
                    if not comment_info:
                        continue
                        
                    # Add comment metadata
                    comment_info.update({
                        'comment_id': comment.id,
                        'comment_score': comment.score,
                        'comment_created_utc': comment.created_utc,
                        'comment_author': str(comment.author) if comment.author else None,
                        'match_confidence': 0.8,  # Slightly lower confidence for comments
                        'matched_product': product,
                        'post_title': submission.title,
                        'post_url': f"https://reddit.com{comment.permalink}"
                    })
                    
                    results['high_confidence'].append(comment_info)
                    
        except Exception as e:
            print(f"Error processing product {product}: {e}")
            continue
    
    return results

def save_to_json(products_data: Dict[str, List[Dict]], base_filename: str) -> Tuple[int, int, List[str]]:
    """
    Save high and low confidence matches to separate JSON files.
    
    Args:
        products_data: Dictionary with 'high_confidence' and 'low_confidence' keys
        base_filename: Base filename (without extension) to use for output files
        
    Returns:
        Tuple of (high_confidence_count, low_confidence_count, filenames)
    """
    output_dir = os.path.join("..", "frontend", "public", "scrapes")
    os.makedirs(output_dir, exist_ok=True)
    
    high_confidence = products_data.get('high_confidence', [])
    low_confidence = products_data.get('low_confidence', [])
    
    # Save high confidence products
    high_filename = os.path.join(output_dir, f"{base_filename}_high_confidence.json")
    with open(high_filename, 'w', encoding='utf-8') as f:
        json.dump(high_confidence, f, ensure_ascii=False, indent=2)
    
    # Save low confidence products
    low_filename = os.path.join(output_dir, f"{base_filename}_low_confidence.json")
    with open(low_filename, 'w', encoding='utf-8') as f:
        json.dump(low_confidence, f, ensure_ascii=False, indent=2)
    
    return len(high_confidence), len(low_confidence), [high_filename, low_filename]

def group_products_by_name(products: List[Dict]) -> Dict[str, Dict]:
    """
    Group a list of product dictionaries by their matched_product field.
    
    Args:
        products: List of product dictionaries to group
        
    Returns:
        Dictionary with product names as keys and product data as values, where each value is a dict containing:
        - product_name: The name of the product
        - comments_count: Total number of comments/reviews
        - megathread_comments: List of comments/reviews for this product
    """
    grouped_products = {}
    
    for product in products:
        # Use the matched_product as the key, or product_name if matched_product is not available
        key = product.get('matched_product', product.get('product_name', 'Unknown'))
        
        # Clean up the key by removing any trailing whitespace
        key = key.strip()
        
        # Initialize the product entry if it doesn't exist
        if key not in grouped_products:
            grouped_products[key] = {
                'product_name': key,
                'comments_count': 0,
                'megathread_comments': []
            }
        
        # Add the comment to the product's megathread_comments
        comment_data = {
            'comment_id': product.get('comment_id'),
            'comment_author': product.get('comment_author'),
            'comment_score': product.get('comment_score'),
            'comment_created_utc': product.get('comment_created_utc'),
            'comment': product.get('comment'),
            'skin_type': product.get('skin_type'),
            'price_size': product.get('price_size'),
            'effects': product.get('effects'),
            'status': product.get('status'),
            'availability': product.get('availability'),
            'match_confidence': product.get('match_confidence'),
            'post_title': product.get('post_title'),
            'post_url': product.get('post_url')
        }
        
        # Add the comment to the product's megathread_comments
        grouped_products[key]['megathread_comments'].append(comment_data)
        
        # Increment the comments count
        grouped_products[key]['comments_count'] += 1
    
    return grouped_products

def combine_posts_data() -> Tuple[int, int]:
    """
    Combine all individual posts JSON files into grouped files
    where products are organized by matched_product.
    
    Returns:
        Tuple of (high_count, low_count) containing the number of products processed
    """
    output_dir = os.path.join("..", "frontend", "public", "scrapes")
    combined_high = []
    combined_low = []
    
    # Find all posts JSON files
    high_files = glob.glob(os.path.join(output_dir, "posts_*_high_confidence.json"))
    low_files = glob.glob(os.path.join(output_dir, "posts_*_low_confidence.json"))
    
    # Remove grouped files from the list to avoid duplicates
    high_files = [f for f in high_files if not f.endswith("_grouped_high_confidence.json")]
    low_files = [f for f in low_files if not f.endswith("_grouped_low_confidence.json")]
    
    # Read and combine all high confidence files
    for file_path in high_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    combined_high.extend(data)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    # Read and combine all low confidence files
    for file_path in low_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    combined_low.extend(data)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    # Group the combined data
    grouped_high = group_products_by_name(combined_high)
    grouped_low = group_products_by_name(combined_low)
    
    # Save the grouped data
    grouped_high_path = os.path.join(output_dir, "posts_grouped_high_confidence.json")
    grouped_low_path = os.path.join(output_dir, "posts_grouped_low_confidence.json")
    
    with open(grouped_high_path, 'w', encoding='utf-8') as f:
        json.dump(grouped_high, f, ensure_ascii=False, indent=2)
    
    with open(grouped_low_path, 'w', encoding='utf-8') as f:
        json.dump(grouped_low, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(grouped_high)} high confidence products and {len(grouped_low)} low confidence products")
    return len(grouped_high), len(grouped_low)

def run_scraper(subreddit_name: str = "beautytalkph", limit_per_product: int = 10) -> None:
    """
    Run the posts scraper with the given parameters.
    
    Args:
        subreddit_name: Name of the subreddit to scrape
        limit_per_product: Maximum number of submissions to process per product
    """
    try:
        print(f"Starting to scrape r/{subreddit_name} for product posts...")
        
        # Scrape product posts
        products_data = scrape_product_submissions(subreddit_name, limit_per_product)
        
        # Save the raw results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        high_count, low_count, _ = save_to_json(products_data, f"posts_{timestamp}")
        
        # Combine with existing data and create grouped files
        total_high, total_low = combine_posts_data()
        
        print(f"Scraping complete. Found {high_count} high confidence and {low_count} low confidence posts.")
        print(f"Total products after combining: {total_high} high confidence, {total_low} low confidence")
        
    except Exception as e:
        print(f"Error running scraper: {e}")

if __name__ == "__main__":
    # Run the scraper with default parameters
    run_scraper(limit_per_product=5)  # Reduce limit for testing
