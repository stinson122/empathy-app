import React, { useEffect, useState } from "react";
import "./HomePage.css";

function HomePage() {
  const [posts, setPosts] = useState([]);
  const [megathreadData, setMegathreadData] = useState({ high_confidence: {}, low_confidence: {} });
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
        
        // Try to load grouped megathread data
        try {
          const [highRes, lowRes] = await Promise.all([
            fetch("/scrapes/products_grouped_high_confidence.json"),
            fetch("/scrapes/products_grouped_low_confidence.json")
          ]);
          
          // Process the responses
          const highData = highRes.ok ? await highRes.json() : {};
          const lowData = lowRes.ok ? await lowRes.json() : {};
          
          // Calculate total counts
          const highCount = Object.values(highData).reduce((sum, product) => sum + (product.comments_count || 0), 0);
          const lowCount = Object.values(lowData).reduce((sum, product) => sum + (product.comments_count || 0), 0);
          
          // Only set data if we have something
          if (highCount > 0 || lowCount > 0) {
            setMegathreadData({
              high_confidence: highData,
              low_confidence: lowData
            });
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
    
    const { high_confidence: highData = {}, low_confidence: lowData = {} } = megathreadData;
    const hasHighConfidence = Object.keys(highData).length > 0;
    const hasLowConfidence = Object.keys(lowData).length > 0;
    
    if (!hasHighConfidence && !hasLowConfidence) {
      return <div className="no-data">No megathread data available. Please run the scraper first.</div>;
    }

    const renderProductCards = (products, isHighConfidence = true) => {
      return Object.entries(products).map(([productName, productData]) => {
        const { comments_count, megathread_comments = [] } = productData;
        
        return (
          <div key={productName} className="product-card">
            <div className="product-header">
              <h3 className="product-name">{productName}</h3>
              <span className="comments-count">{comments_count} {comments_count === 1 ? 'comment' : 'comments'}</span>
            </div>
            
            <div className="comments-container">
              {megathread_comments.map((comment, idx) => (
                <div key={idx} className={`comment ${isHighConfidence ? 'high-confidence' : 'low-confidence'}`}>
                  <div className="comment-content">
                    {comment.effects && (
                      <div className="comment-effects">
                        <strong>Experience:</strong>
                        <p>{comment.effects}</p>
                      </div>
                    )}
                    
                    <div className="comment-details">
                      {comment.skin_type && comment.skin_type.length > 0 && (
                        <p><strong>Skin Type:</strong> {Array.isArray(comment.skin_type) ? comment.skin_type.join(', ') : comment.skin_type}</p>
                      )}
                      {comment.price_size && <p><strong>Price/Size:</strong> {comment.price_size}</p>}
                      {comment.status && <p><strong>Status:</strong> {comment.status}</p>}
                      {comment.availability && <p><strong>Where to buy:</strong> {comment.availability}</p>}
                    </div>
                    
                    <div className="comment-meta">
                      <div className="comment-actions">
                        <a href={`https://reddit.com${comment.comment_id}`} target="_blank" rel="noreferrer" className="comment-link">
                          View comment
                        </a>
                        {comment.comment_created_utc && (
                          <span className="comment-date">{formatDate(comment.comment_created_utc)}</span>
                        )}
                      </div>
                      <div className="comment-info">
                        {comment.comment_author && (
                          <span className="comment-author">u/{comment.comment_author}</span>
                        )}
                        {comment.comment_score !== undefined && (
                          <span className="comment-score">
                            <span className="icon">↑</span> {comment.comment_score}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      });
    };

    return (
      <>
        {hasHighConfidence && (
          <div className="confidence-section">
            <h3 className="confidence-header">
              High Confidence Matches
              <span className="stat high">{Object.keys(highData).length} products</span>
            </h3>
            <div className="products-grid">
              {renderProductCards(highData, true)}
            </div>
          </div>
        )}
        
        {hasLowConfidence && (
          <div className="confidence-section">
            <h3 className="confidence-header">
              Possible Matches
              <span className="stat low">{Object.keys(lowData).length} products</span>
            </h3>
            <div className="products-grid">
              {renderProductCards(lowData, false)}
            </div>
          </div>
        )}
      </>
    );
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
