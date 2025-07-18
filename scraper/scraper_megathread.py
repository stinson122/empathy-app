import praw
import glob
import csv
import json
import os
import difflib
import string
from typing import List, Dict, Optional, Tuple, NamedTuple

# Initialize Reddit instance
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

def extract_product_info(comment_body: str) -> Optional[Dict]:
    """Extract product information from a comment."""
    lines = [line.strip() for line in comment_body.split('\n') if line.strip()]
    if not lines:
        return None
    
    product_info = {
        'skin_type': [],
        'product_name': None,
        'price_size': None,
        'effects': None,
        'status': None,
        'comment': '\n'.join(lines)
    }
    
    # Try to find product name first (required field)
    product_name = None
    for line in lines:
        if 'product' in line.lower() and 'name' in line.lower() and ':' in line:
            product_name = line.split(':', 1)[1].strip()
            break
    
    # If no explicit product name label, try to find a line that looks like a product name
    if not product_name:
        for line in lines:
            # Look for lines that might be product names (not too long, not empty, not starting with common labels)
            if (not any(label in line.lower() for label in ['skin type', 'price', 'size', 'effect', 'experience', 'status', ':']) 
                    and 2 <= len(line) <= 100):
                product_name = line.strip()
                break
    
    if not product_name:
        return None
    
    product_info['product_name'] = product_name
    
    # Parse other fields
    current_field = None
    for line in lines:
        line_lower = line.lower()
        
        if 'skin type' in line_lower and ':' in line:
            current_field = 'skin_type'
            skin_type = line.split(':', 1)[1].strip()
            product_info['skin_type'] = parse_skin_type(skin_type)
        elif 'price' in line_lower and 'size' in line_lower and ':' in line:
            current_field = 'price_size'
            product_info['price_size'] = line.split(':', 1)[1].strip()
        elif ('effect' in line_lower or 'experience' in line_lower) and ':' in line:
            current_field = 'effects'
            product_info['effects'] = line.split(':', 1)[1].strip()
        elif 'status' in line_lower and ':' in line:
            current_field = 'status'
            status = line.split(':', 1)[1].strip().upper()
            if 'HG' in status:
                product_info['status'] = 'HG'
            elif 'WR' in status:
                product_info['status'] = 'WR'
            elif 'WNR' in status:
                product_info['status'] = 'WNR'
        elif current_field == 'effects':
            # Append to effects if we're in the middle of reading a multi-line effects section
            product_info['effects'] = (product_info['effects'] + ' ' + line).strip()
    
    return product_info

class ProductMatch(NamedTuple):
    """Container for product match information."""
    name: str
    confidence: float
    matched_target: str

    @property
    def is_high_confidence(self) -> bool:
        """Determine if this is a high confidence match."""
        return self.confidence >= 0.85

def normalize_text(text: str) -> str:
    """Normalize text for better comparison."""
    # Convert to lowercase and remove punctuation
    text = text.lower().strip()
    text = text.translate(str.maketrans('', '', string.punctuation))
    # Remove common words that don't help with matching
    common_words = {'and', 'the', 'for', 'with', 'with', 'by', 'of', 'in', 'on', 'at', 'to'}
    words = [word for word in text.split() if word not in common_words]
    return ' '.join(words)

def get_products_from_file(filename: str = "products.txt") -> List[str]:
    """Get list of products from a file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Will include all products.")
        return None

def find_best_product_match(product_name: str, target_products: List[str]) -> Optional[ProductMatch]:
    """
    Find the best matching product from the target list using fuzzy matching.
    
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
            return ProductMatch(name=target, confidence=1.0, matched_target=target)
            
        # Check if target is a substring of product name or vice versa
        if (normalized_target in normalized_name or 
            normalized_name in normalized_target):
            ratio = 0.8  # High confidence for substring matches
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = target
        
        # Use sequence matcher for fuzzy matching
        matcher = difflib.SequenceMatcher(None, normalized_name, normalized_target)
        ratio = matcher.ratio()
        
        # If we have a better match, update our best match
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = target
    
    # Only return matches above a certain threshold
    if best_ratio >= 0.68:  # Adjust this threshold as needed
        return ProductMatch(
            name=best_match,
            confidence=best_ratio,
            matched_target=best_match
        )
    
    return None

def scrape_megathread(submission_url: str, limit: int = None, products_file: str = "products.txt") -> Dict[str, List[Dict]]:
    """
    Scrape product information from a megathread submission.
    
    Args:
        submission_url: URL of the Reddit megathread
        limit: Maximum number of comments to process (None for all)
        products_file: Path to file containing list of products to include
        
    Returns:
        Dictionary with two keys:
        - 'high_confidence': List of product info dicts with high confidence matches
        - 'low_confidence': List of product info dicts with lower confidence matches
    """
    try:
        # Get list of target products
        target_products = get_products_from_file(products_file)
        if target_products:
            print(f"Looking for {len(target_products)} products from {products_file}")
        else:
            print("No target products found. Will include all products with product names.")
        
        submission = reddit.submission(url=submission_url)
        submission.comments.replace_more(limit=limit)
        
        # We'll separate results into high and low confidence matches
        results = {
            'high_confidence': [],
            'low_confidence': []
        }
        
        for comment in submission.comments.list():
            if not comment.body or comment.body == '[deleted]' or comment.body == '[removed]':
                continue
                
            product_info = extract_product_info(comment.body)
            if not product_info or not product_info['product_name']:
                continue
                
            # If no target products, include everything in high confidence
            if not target_products:
                product_info.update({
                    'comment_id': comment.id,
                    'comment_score': comment.score,
                    'comment_created_utc': comment.created_utc,
                    'comment_author': str(comment.author) if comment.author else None,
                    'match_confidence': 1.0,
                    'matched_product': product_info['product_name']
                })
                results['high_confidence'].append(product_info)
                continue
                
            # Try to find a matching product
            match = find_best_product_match(product_info['product_name'], target_products)
            if match:
                # Add match information to the product info
                product_info.update({
                    'comment_id': comment.id,
                    'comment_score': comment.score,
                    'comment_created_utc': comment.created_utc,
                    'comment_author': str(comment.author) if comment.author else None,
                    'match_confidence': match.confidence,
                    'matched_product': match.matched_target
                })
                
                # Categorize based on match confidence
                if match.is_high_confidence:
                    results['high_confidence'].append(product_info)
                else:
                    results['low_confidence'].append(product_info)
        
        return results
    except Exception as e:
        print(f"Error scraping megathread: {e}")
        return []

def save_products_to_csv(products: List[Dict], filename: str, match_type: str = ""):
    """Save product information to a CSV file."""
    if not products:
        return 0
    
    fieldnames = [
        'matched_product', 'match_confidence', 'product_name', 'skin_type', 
        'price_size', 'effects', 'status', 'comment_id', 'comment_score', 
        'comment_created_utc', 'comment_author', 'comment'
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for product in products:
            # Create a copy to avoid modifying the original
            product_csv = product.copy()
            
            # Convert skin_type list to string for CSV
            product_csv['skin_type'] = ', '.join(product['skin_type']) if product['skin_type'] else ''
            
            # Round match confidence for readability
            if 'match_confidence' in product_csv:
                product_csv['match_confidence'] = round(product_csv['match_confidence'], 2)
            
            writer.writerow(product_csv)
    
    return len(products)

def save_to_csv(products_data: Dict[str, List[Dict]], base_filename: str):
    """
    Save high and low confidence matches to separate CSV files.
    
    Args:
        products_data: Dictionary with 'high_confidence' and 'low_confidence' keys
        base_filename: Base filename (without extension) to use for output files
        
    Returns:
        Tuple of (high_confidence_count, low_confidence_count, filenames)
    """
    high_confidence = products_data.get('high_confidence', [])
    low_confidence = products_data.get('low_confidence', [])
    
    # Create the public/scrapes directory if it doesn't exist
    os.makedirs('../frontend/public/scrapes', exist_ok=True)
    
    filenames = []
    
    # Save high confidence matches
    if high_confidence:
        filename = f"../frontend/public/scrapes/{base_filename}_high_confidence.csv"
        save_products_to_csv(high_confidence, filename, "high_confidence")
        filenames.append(filename)
    
    # Save low confidence matches if there are any
    if low_confidence:
        filename = f"../frontend/public/scrapes/{base_filename}_low_confidence.csv"
        save_products_to_csv(low_confidence, filename, "low_confidence")
        filenames.append(filename)
    
    return len(high_confidence), len(low_confidence), filenames


def save_to_json(products_data: Dict[str, List[Dict]], base_filename: str):
    """
    Save high and low confidence matches to separate JSON files.
    
    Args:
        products_data: Dictionary with 'high_confidence' and 'low_confidence' keys
        base_filename: Base filename (without extension) to use for output files
        
    Returns:
        Tuple of (high_confidence_count, low_confidence_count, filenames)
    """
    high_confidence = products_data.get('high_confidence', [])
    low_confidence = products_data.get('low_confidence', [])
    
    filenames = []
    
    # Create the public/scrapes directory if it doesn't exist
    os.makedirs('../frontend/public/scrapes', exist_ok=True)
    
    # Save high confidence matches
    if high_confidence:
        filename = f"../frontend/public/scrapes/{base_filename}_high_confidence.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(high_confidence, f, ensure_ascii=False, indent=2)
        filenames.append(filename)
    
    # Save low confidence matches if there are any
    if low_confidence:
        filename = f"../frontend/public/scrapes/{base_filename}_low_confidence.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(low_confidence, f, ensure_ascii=False, indent=2)
        filenames.append(filename)
    
    # Update combined files
    high_count, low_count = combine_megathread_data()
    print(f"Updated combined files with {high_count} high confidence and {low_count} low confidence products")
    
    return len(high_confidence), len(low_confidence), filenames

def combine_megathread_data():
    """
    Combine all individual megathread JSON files into combined files.
    
    Returns:
        Tuple of (combined_high, combined_low) counts
    """
    output_dir = '../frontend/public/scrapes'
    combined_high = []
    combined_low = []
    
    # Find all high and low confidence JSON files
    high_files = glob.glob(f"{output_dir}/*_high_confidence.json")
    low_files = glob.glob(f"{output_dir}/*_low_confidence.json")
    
    # Skip the combined files if they exist
    combined_high_path = f"{output_dir}/products_all_high_confidence.json"
    combined_low_path = f"{output_dir}/products_all_low_confidence.json"
    
    high_files = [f for f in high_files if not f.endswith('_all_high_confidence.json')]
    low_files = [f for f in low_files if not f.endswith('_all_low_confidence.json')]
    
    # Load and combine high confidence files
    for filepath in high_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    combined_high.extend(data)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error reading {filepath}: {e}")
    
    # Load and combine low confidence files
    for filepath in low_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    combined_low.extend(data)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error reading {filepath}: {e}")
    
    # Save combined files
    if combined_high:
        with open(combined_high_path, 'w', encoding='utf-8') as f:
            json.dump(combined_high, f, ensure_ascii=False, indent=2)
    
    if combined_low:
        with open(combined_low_path, 'w', encoding='utf-8') as f:
            json.dump(combined_low, f, ensure_ascii=False, indent=2)
    
    return len(combined_high), len(combined_low)

def run_scraper(submission_urls: list, limit: int = None, products_file: str = "products.txt"):
    """
    Run the megathread scraper with the given submission URL.
    
    Args:
        submission_url: URL of the Reddit megathread to scrape
        limit: Maximum number of comments to process (None for all)
        products_file: Path to file containing list of products to include
    """
    
    # Get the base output filename from the products file
    base_name = os.path.splitext(os.path.basename(products_file))[0]
    all_results = {}
    
    for url in submission_urls:
        print(f"\n{'='*50}")
        print(f"Scraping megathread: {url}")
        print(f"{'='*50}")

        # Scrape the megathread
        products_data = scrape_megathread(url, limit=limit, products_file=products_file)
        all_results[url] = products_data
                
        # Extract a unique identifier from the URL (e.g., the reddit post ID)
        thread_id = url.split('/')[-2] if '/' in url else 'thread'
        thread_base_name = f"{base_name}_{thread_id}"
        
        # Save results if we found any products
        if any(products_data.values()):
            # Save to CSV and JSON
            hc_csv, lc_csv, csv_files = save_to_csv(products_data, thread_base_name)
            hc_json, lc_json, json_files = save_to_json(products_data, thread_base_name)
            
            # Print a single summary
            total_high = len(products_data.get('high_confidence', []))
            total_low = len(products_data.get('low_confidence', []))
            
            print(f"\nScraping complete! Found {total_high} high confidence and {total_low} low confidence matches.")
            print("Saved files:")
            for f in csv_files + json_files:
                print(f"- {os.path.basename(f)}")
        else:
            print("No matching products found in the megathread.")
    
    return all_results

if __name__ == "__main__":
    # List of megathreads to scrape
    MEGATHREADS = [
        "http://reddit.com/r/beautytalkph/comments/1daza0o/megathread_facial_cleanser_first_or_second_2024/",
        "https://www.reddit.com/r/beautytalkph/comments/17ss0yq/product_megathread_facial_wash_cleansers_first/",
        "https://www.reddit.com/r/beautytalkph/comments/1kkm5g8/sunscreen_megathread_2025/",
        "https://www.reddit.com/r/beautytalkph/comments/119p88g/product_megathread_sunscreens_2023/",
        "https://www.reddit.com/r/beautytalkph/comments/1biv527/product_megathread_sunscreens_2024/",
        "https://www.reddit.com/r/beautytalkph/comments/1kkm5g8/sunscreen_megathread_2025/"

    ]
    
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    products_file = os.path.join(script_dir, "products.txt")
    
    run_scraper(
        submission_urls=MEGATHREADS,
        limit=500,  # Set limit to None to get all comments
        products_file=products_file
    )
