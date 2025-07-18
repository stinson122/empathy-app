import React, { useEffect, useState } from "react";
import "./HomePage.css";

function HomePage() {
  const [posts, setPosts] = useState([]);
  const [megathreadData, setMegathreadData] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        // Load regular posts
        const postsResponse = await fetch("/scraped.json");
        const postsData = await postsResponse.json();
        setPosts(postsData.slice(0, 5)); // Show only first 5 posts
        
        // Try to load combined megathread data
        const megathreadPaths = [
          "/scrapes/products_all_high_confidence.json",
          "/scrapes/products_all_low_confidence.json"
        ];
        
        try {
          // Load both high and low confidence combined files
          const [highRes, lowRes] = await Promise.all([
            fetch(megathreadPaths[0]),
            fetch(megathreadPaths[1])
          ]);
          
          // Check if we got at least one valid response
          if (highRes.ok || lowRes.ok) {
            const highData = highRes.ok ? await highRes.json() : [];
            const lowData = lowRes.ok ? await lowRes.json() : [];
            
            // Format the data for the component
            const combinedData = {
              'all_megathreads': {
                high_confidence: Array.isArray(highData) ? highData : [],
                low_confidence: Array.isArray(lowData) ? lowData : []
              }
            };
            
            setMegathreadData(combinedData);
            return;
          }
        } catch (e) {
          console.error("Error loading megathread data:", e);
          throw e; // Re-throw to be caught by the outer try-catch
        }
        
        // If we get here, all fetch attempts failed
        setError("Could not load megathread data. Please run the scraper first.");
      } catch (error) {
        console.error("Error loading data:", error);
        setError("Failed to load data. Please check the console for details.");
      } finally {
        setIsLoading(false);
      }
    };
    
    loadData();
  }, []);

  const formatDate = (timestamp) => {
    if (!timestamp) return '';
    try {
      const date = new Date(timestamp * 1000);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (e) {
      return '';
    }
  };

  const renderMegathreadResults = () => {
    if (isLoading) {
      return (
        <div className="loading">
          <div className="spinner"></div>
          <p>Loading megathread data...</p>
        </div>
      );
    }
    
    if (error) {
      return <div className="error-message">{error}</div>;
    }
    
    const threadUrls = Object.keys(megathreadData);
    if (threadUrls.length === 0) {
      return <div className="no-data">No megathread data available. Please run the scraper first.</div>;
    }

    return threadUrls.map((url, idx) => {
      const thread = megathreadData[url];
      const highConfidence = thread.high_confidence || [];
      const lowConfidence = thread.low_confidence || [];
      const allProducts = [...highConfidence, ...lowConfidence];
      
      // Extract thread title from URL or use a default
      const threadTitle = url.split('/').filter(Boolean).pop().replace(/_/g, ' ') || 'Megathread';

      return (
        <div key={idx} className="megathread-section">
          <div className="megathread-header">
            <h2 className="megathread-title">{threadTitle}</h2>
            <div className="thread-stats">
              {highConfidence.length > 0 && (
                <span className="stat high">{highConfidence.length} high confidence</span>
              )}
              {lowConfidence.length > 0 && (
                <span className="stat low">{lowConfidence.length} possible matches</span>
              )}
              <a href={url} target="_blank" rel="noreferrer" className="source-link">
                View thread ↗
              </a>
            </div>
          </div>
          
          {allProducts.length === 0 ? (
            <p>No matching products found in this thread.</p>
          ) : (
            <div className="products-container">
              {allProducts.map((product, pIdx) => (
                <div key={`${idx}-${pIdx}`} className={`product-card ${product.match_confidence >= 0.85 ? 'high-confidence' : 'low-confidence'}`}>
                  <div className="product-header">
                    <h3 className="product-name">{product.matched_product || product.product_name}</h3>
                    <span className="confidence-badge">
                      {product.match_confidence >= 0.85 ? '✓' : '~'} {(product.match_confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  
                  <div className="product-details">
                    {product.skin_type && product.skin_type.length > 0 && (
                      <p><strong>Skin Type:</strong> {Array.isArray(product.skin_type) ? product.skin_type.join(', ') : product.skin_type}</p>
                    )}
                    {product.price_size && <p><strong>Price/Size:</strong> {product.price_size}</p>}
                    {product.status && <p><strong>Status:</strong> {product.status}</p>}
                    {product.effects && (
                      <div className="effects">
                        <strong>Experience:</strong>
                        <p>{product.effects}</p>
                      </div>
                    )}
                    <div className="comment-meta">
                      <div className="comment-actions">
                        <a href={`https://reddit.com${product.comment_id}`} target="_blank" rel="noreferrer" className="comment-link">
                          View comment
                        </a>
                        {product.comment_created_utc && (
                          <span className="comment-date">{formatDate(product.comment_created_utc)}</span>
                        )}
                      </div>
                      <div className="comment-info">
                        {product.comment_author && (
                          <span className="comment-author">u/{product.comment_author}</span>
                        )}
                        {product.comment_score !== undefined && (
                          <span className="comment-score">
                            <span className="icon">↑</span> {product.comment_score}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      );
    });
  };

  return (
    <div className="app-container">
      <div className="container">
        <h1 className="header">Reddit Product Reviews</h1>
        {/*
        <section className="section">
          <h2>Recent Posts</h2>
          {posts.map((post, idx) => (
            <div key={idx} className="post">
              <h3 className="title">{post.title}</h3>
              <p className="body">{post.body}</p>
              <a href={post.url} target="_blank" rel="noreferrer" className="link">View on Reddit</a>
              <div className="comments-section">
                <h4>Comments:</h4>
                <ul>
                  {post.comments?.slice(0, 3).map((comment, i) => (
                    <li key={i}>{comment}</li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </section>*/
        }

        <section className="section megathreads-section">
          <div className="section-header">
            <h2>Megathread Results</h2>
            <p className="section-description">
              Product mentions from beauty community megathreads, matched with confidence scores
            </p>
          </div>
          {renderMegathreadResults()}
        </section>
      </div>
    </div>
  );
}

export default HomePage;
