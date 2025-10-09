import React, { useState } from 'react'
import ThreeStepPractice from './components/ThreeStepPractice'
import PronunciationPractice from './components/PronunciationPractice'

function App() {
  const [page, setPage] = useState('practice')
  return (
    <div>
      {page === 'practice' ? (
        <PronunciationPractice page={page} setPage={setPage} />
      ) : (
        <ThreeStepPractice page={page} setPage={setPage} />
      )}
    </div>
  )
}

export default App
