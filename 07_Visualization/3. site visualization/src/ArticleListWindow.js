// frontend/src/ArticleListWindow.js

import React from 'react';
import './ArticleListWindow.css';

const ArticleListWindow = ({ articles }) => {
  return (
    <div className="article-list-window">
      <h2>선택된 기사 목록 ({articles.length}개)</h2>
      <ul className="article-list">
        {articles.length > 0 ? (
          articles.map(article => (
            <li key={article.id} className="article-item">
              <a href={article.url} target="_blank" rel="noopener noreferrer">
                {article.title}
              </a>
            </li>
          ))
        ) : (
          <p>선택된 지역의 기사가 없습니다.</p>
        )}
      </ul>
    </div>
  );
};

export default ArticleListWindow;