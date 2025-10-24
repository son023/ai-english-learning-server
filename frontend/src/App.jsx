import React, { useState } from 'react'
import ThreeStepPractice from './components/ThreeStepPractice'
import PronunciationPractice from './components/PronunciationPractice'
import WordPronunciationLearning from './components/WordPronunciationLearning'

function App() {
  const [page, setPage] = useState('practice')
  
  const renderPage = () => {
    switch(page) {
      case 'practice':
        return <PronunciationPractice page={page} setPage={setPage} />
      case 'word-learning':
        return <WordPronunciationLearning page={page} setPage={setPage} />
      case 'three-step':
        return <ThreeStepPractice page={page} setPage={setPage} />
      default:
        return <PronunciationPractice page={page} setPage={setPage} />
    }
  }

  return (
    <div>
      {renderPage()}
    </div>
  )
}

export default App
