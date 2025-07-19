import React, { useEffect, useState } from "react";
import "./HomePage.css";

function HomePage() {
  const [combinedData, setCombinedData] = useState({ high_confidence: {}, low_confidence: {} });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        // Load combined data for both confidence levels
        const [highRes, lowRes] = await Promise.all([
          fetch("/scrapes/combined_data_high_confidence.json"),
          fetch("/scrapes/combined_data_low_confidence.json")
        ]);
        
        if (!highRes.ok || !lowRes.ok) {
          throw new Error("Failed to load one or more data files");
        }
        
        const highData = await highRes.json();
        const lowData = await lowRes.json();
        
        setCombinedData({
          high_confidence: highData,
          low_confidence: lowData
        });
        
      } catch (error) {
        console.error("Error loading data:", error);
        setError("Failed to load data. Please make sure you've run the scraper first.");
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
          <p>Loading product data...</p>
        </div>
      );
    }
    
    if (error) {
      return <div className="error-message">{error}</div>;
    }
    
    const { high_confidence: highData = {}, low_confidence: lowData = {} } = combinedData;
    const hasHighConfidence = Object.keys(highData).length > 0;
    const hasLowConfidence = Object.keys(lowData).length > 0;
    
    if (!hasHighConfidence && !hasLowConfidence) {
      return <div className="no-data">No product data available. Please run the scraper first.</div>;
    }

    const renderProductCards = (products, isHighConfidence = true) => {
      return Object.entries(products).map(([productName, productData]) => {
        const { comments_count = 0, posts_count = 0, megathread_comments = [], posts = [] } = productData;
        const totalItems = comments_count + posts_count;
        
        return (
          <div key={productName} className="product-card">
            <div className="product-header">
              <div>
                <h3 className="product-name">{productName}</h3>
                {productData.product_type && (
                  <span className="product-type">{productData.product_type}</span>
                )}
              </div>
              <div className="counts">
                {posts_count > 0 && <span className="posts-count">{posts_count} {posts_count === 1 ? 'post' : 'posts'}</span>}
                {comments_count > 0 && <span className="comments-count">{comments_count} {comments_count === 1 ? 'comment' : 'comments'}</span>}
              </div>
            </div>
            
            {/* Render posts */}
            {posts.length > 0 && (
              <div className="posts-container">
                <h4 className="section-title">From Posts</h4>
                {posts.map((post, idx) => (
                  <div key={`post-${idx}`} className={`post ${isHighConfidence ? 'high-confidence' : 'low-confidence'}`}>
                    <div className="post-content">
                      {post.post_selftext && (
                        <div className="post-effects">
                          <strong>Content:</strong>
                          <div className="post-excerpt">
                            {post.post_selftext}
                          </div>
                        </div>
                      )}
                      
                      <div className="post-details">
                        {post.skin_type && post.skin_type.length > 0 && (
                          <p><strong>Skin Type:</strong> {Array.isArray(post.skin_type) ? post.skin_type.join(', ') : post.skin_type}</p>
                        )}
                        {post.price_size && <p><strong>Price/Size:</strong> {post.price_size}</p>}
                        {post.status && <p><strong>Status:</strong> {post.status}</p>}
                        {post.availability && <p><strong>Where to buy:</strong> {post.availability}</p>}
                      </div>
                      
                      <div className="post-meta">
                        <div className="post-actions">
                          <a href={`https://reddit.com${post.post_id}`} target="_blank" rel="noreferrer" className="post-link">
                            View post
                          </a>
                          {post.post_created_utc && (
                            <span className="post-date">{formatDate(post.post_created_utc)}</span>
                          )}
                        </div>
                        <div className="post-info">
                          {post.post_author && (
                            <span className="post-author">u/{post.post_author}</span>
                          )}
                          {post.post_score !== undefined && (
                            <span className="post-score">
                              <span className="icon">↑</span> {post.post_score}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            {/* Render megathread comments */}
            {megathread_comments.length > 0 && (
              <div className="comments-container">
                <h4 className="section-title">From Megathreads</h4>
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
            )}
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
        
        <section className="section products-section">
          <div className="section-header">
            <h2>Product Reviews</h2>
            <p className="section-description">
              Product mentions from both individual posts and megathreads, grouped by confidence level
            </p>
          </div>
          {renderMegathreadResults()}
        </section>
      </div>
    </div>
  );
}

export default HomePage;
