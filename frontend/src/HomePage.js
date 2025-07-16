import React, { useEffect, useState } from "react";
import "./HomePage.css";

const HomePage = () => {
  const [posts, setPosts] = useState([]);

  useEffect(() => {
    fetch("/scraped.json")
      .then((res) => res.json())
      .then((data) => setPosts(data));
  }, []);

  return (
    <div className="homepage">
      <h1>Reddit Product Reviews</h1>
      {posts.map((product, index) => (
        <div key={index} className="product-section">
          <h2>{product.product}</h2>
          {product.posts.map((post, idx) => (
            <div key={idx} className="post">
              <a href={post.url} target="_blank" rel="noopener noreferrer">
                {post.title}
              </a>
              <p>{post.content}</p>
              <ul>
                {post.comments.map((comment, cidx) => (
                  <li key={cidx}>{comment}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
};

export default HomePage;
