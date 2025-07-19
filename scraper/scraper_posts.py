import os
import re
import json
import glob
import difflib
import praw
from typing import List, Dict, Optional, Tuple, NamedTuple, Set
from datetime import datetime
from urllib.parse import urlparse

# Initialize Reddit instance
reddit = praw.Reddit(
    client_id="Wt3DQHzvtI4_poBQ58Rn2g",
    client_secret="ilhFDto6TafES55zhDrQPJnyJ28ZOw",
    password="Dlsugrad#12",
    user_agent="script:reddit_scraper:v1.0",
    username="Successful_Body674",
)

# Confidence thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.85
LOW_CONFIDENCE_THRESHOLD = 0.72

class ProductMatch(NamedTuple):
    """Container for product match information."""
    name: str
    confidence: float
    matched_target: str

    @property
    def is_high_confidence(self) -> bool:
        """Determine if this is a high confidence match."""
        return self.confidence >= HIGH_CONFIDENCE_THRESHOLD

def normalize_text(text: str) -> str:
    """Normalize text for better comparison."""
    if not text:
        return ""
    # Convert to lowercase and remove punctuation
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()

def find_best_product_match(product_name: str, target_products: List[str]) -> Optional[ProductMatch]:
    """
    Find the best matching product from the target list using fuzzy matching.
    
    Args:
        product_name: The product name to match
        target_products: List of target product names to match against
        
    Returns:
        ProductMatch if a good match is found, None otherwise
    """
    if not target_products:
        return None
        
    normalized_name = normalize_text(product_name)
    best_match = None
    best_ratio = 0
    
    for target in target_products:
        normalized_target = normalize_text(target)
        
        # Check for exact match (after normalization)
        if normalized_name == normalized_target:
            return ProductMatch(name=product_name, confidence=1.0, matched_target=target)
            
        # Check for substring match
        if normalized_name in normalized_target or normalized_target in normalized_name:
            return ProductMatch(name=product_name, confidence=0.8, matched_target=target)
            
        # Use sequence matcher for fuzzy matching
        matcher = difflib.SequenceMatcher(None, normalized_name, normalized_target)
        ratio = matcher.ratio()
        
        # If we have a better match, update our best match
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = target
    
    # Only return matches above a certain threshold
    if best_ratio >= 0.68:
        return ProductMatch(
            name=best_match,
            confidence=best_ratio,
            matched_target=best_match
        )
    
    return None

def calculate_confidence(product_info: Dict) -> float:
    """
    Calculate confidence score based on extracted information.
    
    Scoring:
    - Base score: 0.5 (product name was found in search)
    - Exact product name in title: +0.3
    - Exact product name in content: +0.2
    - Skin type: +0.1
    - Price/size: +0.1
    - Status: +0.15
    - Availability: +0.15
    - Max score: 1.0
    """
    score = 0.5  # Base score for matching product name in search
    
    # Get product name, title, and content
    product_name = product_info.get('product_name', '')
    post_title = product_info.get('post_title', '')
    comment = product_info.get('comment', '')
    
    # Normalize text for comparison
    normalized_name = normalize_text(product_name)
    normalized_title = normalize_text(post_title)
    normalized_comment = normalize_text(comment)
    
    # Check for exact match in title (higher weight)
    if normalized_name and normalized_name in normalized_title:
        score += 0.3
    # Check for exact match in content (lower weight)
    elif normalized_name and normalized_name in normalized_comment:
        score += 0.2
    
    # Increase score for each piece of information found
    if product_info.get('skin_type'):
        score += 0.1
    if product_info.get('price_size'):
        score += 0.1
    if product_info.get('status'):
        score += 0.15
    if product_info.get('availability'):
        score += 0.15
    
    # Cap at 1.0
    return min(score, 1.0)

def extract_skin_type(text: str) -> List[str]:
    """Extract skin type from text."""
    skin_types = []
    text_lower = text.lower()
    
    # Common skin type patterns
    patterns = {
        'oily': r'(?:have|has|with|my|i\'ve got|i have|i\'m) (?:very |really |extremely |super )?(oily|oil|oily skin|oil skin)',
        'dry': r'(?:have|has|with|my|i\'ve got|i have|i\'m) (?:very |really |extremely |super )?(dry|dry skin|drying)',
        'combination': r'(?:have|has|with|my|i\'ve got|i have|i\'m) (?:very |really |extremely |super )?(combination|combi|combo|combined)',
        'sensitive': r'(?:have|has|with|my|i\'ve got|i have|i\'m) (?:very |really |extremely |super )?(sensitive|sensitivity|irritated|irritation)',
        'acne': r'(?:have|has|with|my|i\'ve got|i have|i\'m) (?:very |really |extremely |super )?(acne|pimple|breakout|break out)',
        'normal': r'(?:have|has|with|my|i\'ve got|i have|i\'m) (?:very |really |extremely |super )?(normal|balanced)'
    }
    
    # Check for each skin type
    for skin_type, pattern in patterns.items():
        if re.search(pattern, text_lower):
            skin_types.append(skin_type.capitalize())
    
    return skin_types

def extract_price_size(text: str) -> Optional[str]:
    """Extract price and size information from text."""
    # Look for common price patterns (e.g., PHP 1,234.56, $12.34, 1000)
    price_patterns = [
        r'(?:PHP|Php|php|₱)\s*[\d,]+(?:\.\d{2})?'  # PHP 1,234.56 or PHP 1234.56
    ]
    
    # Look for size/volume patterns (e.g., 100ml, 1.7oz, 50g)
    size_patterns = [
        r'\b\d+(?:\.\d+)?\s*(?:ml|mL|ML|oz|fl\.?\s*oz|g|gram|grams|kg|kilogram|kilograms)\b',
        r'\b(?:one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:ml|mL|ML|oz|fl\.?\s*oz|g|gram|grams|kg|kilogram|kilograms)\b'
    ]
    
    # Search for price and size in text
    price_match = None
    size_match = None
    
    for pattern in price_patterns:
        match = re.search(pattern, text)
        if match:
            price_match = match.group(0).strip()
            break
    
    for pattern in size_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            size_match = match.group(0).strip()
            break
    
    # Combine price and size if both found
    if price_match and size_match:
        return f"{price_match} ({size_match})"
    elif price_match:
        return price_match
    elif size_match:
        return f"Size: {size_match}"
    
    return None

def extract_status(text: str) -> Optional[str]:
    """Extract status (WR, WNR, etc.) from text."""
    text_upper = text.upper()
    
    # Check for status patterns
    wr_patterns = [
        r'\bWR\b',
        r'will repurchase',
        r'would repurchase',
        r'will buy again',
        r'would buy again',
        r'repurchase: yes',
        r'repurchase\s*\?\s*yes'
    ]
    
    wnr_patterns = [
        r'\bWNR\b',
        r'\bWNRP\b',
        r'will not repurchase',
        r'would not repurchase',
        r'won\'t repurchase',
        r'repurchase: no',
        r'repurchase\s*\?\s*no',
        r'would not buy again',
        r'will not buy again',
        r'won\'t buy again'
    ]
    
    hg_patterns = [
        r'\bHG\b',
        r'holy grail'
    ]
    
    # Check patterns in order of specificity
    for pattern in hg_patterns:
        if re.search(pattern, text_upper, re.IGNORECASE):
            return 'HG (Holy Grail)'
            
    for pattern in wr_patterns:
        if re.search(pattern, text_upper, re.IGNORECASE):
            return 'WR (Will Repurchase)'
            
    for pattern in wnr_patterns:
        if re.search(pattern, text_upper, re.IGNORECASE):
            return 'WNR (Will Not Repurchase)'
            
    return None

def extract_availability(text: str) -> Optional[str]:
    """Extract availability information."""
    text_lower = text.lower()
    
    # Common places where products are bought
    places = [
        'watsons', 'shopee', 'lazada', 'online store', 'supermarket'
    ]
    
    # Common phrases indicating purchase location
    phrases = [
        r'bought (?:from|at|on|via)',
        r'purchased (?:from|at|on|via)',
        r'available (?:at|on|in|from)',
        r'i (?:bought|purchased|got) (?:it|this|one) (?:from|at|on|via)',
        r'found (?:it|this) (?:at|on|in|from)',
        r'selling (?:at|on|in|via|through)'
    ]
    
    # Check for places
    for place in places:
        if place in text_lower:
            return place.title()
    
    # Check for phrases and extract the following text
    for phrase in phrases:
        match = re.search(f"{phrase}\s*([^\n.,;:!?]+)", text_lower)
        if match:
            return match.group(1).strip().capitalize()
    
    return None

def is_spam_comment(text: str) -> bool:
    """Check if a comment is likely spam."""
    if not text:
        return False
        
    text_lower = text.lower()
    
    # Common spam indicators
    spam_indicators = [
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',  # URLs
        r'@\w+',  # @mentions
        r'\b(?:order|discount|promo|offer|deal)\b',  # Commercial terms
        r'\b(?:contact|call|text|whatsapp|viber|telegram|dm|message|pm)\b',
        r'\b(?:follow|like|share|subscribe|join|channel|group|page)\b',
        r'\b(?:free|giveaway|contest|raffle|prize|reward|voucher|coupon|code)\b',
        r'\b(?:check out|visit|click|link|website|site|store|shop|seller|vendor)\b',
        r'\b(?:limited|stock|available|hurry|rush|last|few|left|only)\b',
        r'\b(?:guarantee|warranty|refund|return|exchange|shipping|delivery)\b'
    ]
    
    # Check for multiple spam indicators
    spam_count = 0
    for pattern in spam_indicators:
        if re.search(pattern, text_lower):
            spam_count += 1
            if spam_count >= 3:  # Multiple spam indicators likely means it's spam
                return True
    
    return False

def extract_product_info(text: str, product_name: str, post_title: str = '') -> Optional[Dict]:
    """
    Extract product information from submission text.
    
    Args:
        text: The text content to extract information from
        product_name: The name of the product being searched for
        post_title: The title of the post (optional)
        
    Returns:
        Dictionary containing extracted product information, or None if no relevant info found
    """
    if not text or not text.strip():
        return None
    
    # Check if this is likely spam
    if is_spam_comment(text):
        return None
    
    # Initialize product info with basic data
    product_info = {
        'product_name': product_name,
        'post_title': post_title,
        'comment': text.strip(),
        'skin_type': extract_skin_type(text),
        'price_size': extract_price_size(text),
        'status': extract_status(text),
        'availability': extract_availability(text),
        'match_confidence': 0.0
    }
    
    # Calculate confidence score
    product_info['match_confidence'] = calculate_confidence(product_info)
    
    # Only return if we have at least some confidence
    if product_info['match_confidence'] >= LOW_CONFIDENCE_THRESHOLD:
        return product_info
    
    return None

def scrape_product_submissions(subreddit_name: str = "beautytalkph", limit_per_product: int = 10) -> Dict[str, List[Dict]]:
    """
    Scrape product-specific submissions from a subreddit.
    
    Args:
        subreddit_name: Name of the subreddit to scrape
        limit_per_product: Maximum number of submissions to process per product
        
    Returns:
        Dictionary with two keys:
        - 'high_confidence': List of product info dicts with high confidence matches (>=0.85)
        - 'low_confidence': List of product info dicts with medium confidence matches (0.72-0.849)
    """
    # Get list of target products
    products = get_products_from_file()
    if not products:
        print("No products found in products.txt. Please add products to search for.")
        return {'high_confidence': [], 'low_confidence': []}
    
    results = {
        'high_confidence': [],
        'low_confidence': []
    }
    
    for product in products:
        try:
            print(f"Searching for posts about: {product}")
            
            # Search for posts containing the product name
            for submission in reddit.subreddit(subreddit_name).search(f'title:{product}', limit=limit_per_product):
                try:
                    # Skip removed or deleted posts
                    if submission.selftext in ['[removed]', '[deleted]']:
                        continue
                    
                    # Extract product info from post
                    product_info = extract_product_info(
                        text=submission.selftext,
                        product_name=product,
                        post_title=submission.title
                    )
                    
                    if not product_info:
                        continue
                    
                    # Add post metadata
                    product_info.update({
                        'post_id': submission.id,
                        'post_url': f"https://reddit.com{submission.permalink}",
                        'post_score': submission.score,
                        'post_created_utc': submission.created_utc,
                        'post_author': str(submission.author) if submission.author else None
                    })
                    
                    # Categorize by confidence
                    confidence = product_info.get('match_confidence', 0)
                    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
                        results['high_confidence'].append(product_info)
                    elif confidence >= LOW_CONFIDENCE_THRESHOLD:
                        results['low_confidence'].append(product_info)
                        
                except Exception as e:
                    print(f"Error processing submission {submission.id}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error searching for product {product}: {e}")
            continue
    
    return results

def get_products_from_file(filename: str = "products.txt") -> List[str]:
    """
    Read product names from a file.
    
    Args:
        filename: Path to the file containing product names (one per line)
        
    Returns:
        List of product names
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Warning: {filename} not found. No product filtering will be applied.")
        return []

def save_to_json(products_data: Dict[str, List[Dict]], base_filename: str) -> Tuple[int, int, List[str]]:
    """
    Save product data to JSON files.
    
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
    Group a list of post dictionaries by their product_name field.
    
    Args:
        products: List of post dictionaries to group
        
    Returns:
        Dictionary with product names as keys and product data as values, where each value is a dict containing:
        - product_name: The name of the product
        - posts_count: Total number of posts for this product
        - posts: List of posts for this product with their details
    """
    grouped_products = {}
    
    for post in products:
        # Use the matched product name as the key
        key = post.get('matched_product', post.get('product_name', 'unknown'))
        
        # Initialize product data if not exists
        if key not in grouped_products:
            grouped_products[key] = {
                'product_name': key,
                'posts_count': 0,
                'posts': []
            }
        
        # Add post data
        post_data = {
            'post_id': post.get('post_id'),
            'post_author': post.get('post_author'),
            'post_score': post.get('post_score'),
            'post_created_utc': post.get('post_created_utc'),
            'post_title': post.get('post_title'),
            'post_url': post.get('post_url'),
            'post_selftext': post.get('comment', ''),
            'match_confidence': post.get('match_confidence'),
            'skin_type': post.get('skin_type'),
            'price_size': post.get('price_size'),
            'status': post.get('status'),
            'availability': post.get('availability')
        }
        
        # Add the post to the product's posts list
        grouped_products[key]['posts'].append(post_data)
        
        # Increment the posts count
        grouped_products[key]['posts_count'] += 1
    
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
    
    # Load and combine high confidence files
    for file in high_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    combined_high.extend(data)
        except Exception as e:
            print(f"Error loading {file}: {e}")
    
    # Load and combine low confidence files
    for file in low_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    combined_low.extend(data)
        except Exception as e:
            print(f"Error loading {file}: {e}")
    
    # Group products by name
    grouped_high = list(group_products_by_name(combined_high).values())
    grouped_low = list(group_products_by_name(combined_low).values())
    
    # Save grouped files
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
