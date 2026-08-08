import React, { useEffect, useState } from 'react';
import { BookOpenCheck, Check, ChevronLeft, ChevronRight, Clock3, Flame, Plus, RotateCw, X } from 'lucide-react';
import { DueReview, Flashcard } from '../types';

interface Props { flashcards: Flashcard[]; dueReviews: DueReview[]; onCreateFlashcard: (fc: { front: string; back: string; difficulty: number }) => Promise<void>; onReviewFlashcard: (id: string, rating: 'again' | 'hard' | 'good' | 'easy') => Promise<void>; }

export const LearningTab: React.FC<Props> = ({ flashcards, dueReviews, onCreateFlashcard, onReviewFlashcard }) => {
  const [showModal, setShowModal] = useState(false); const [front, setFront] = useState(''); const [back, setBack] = useState(''); const [difficulty, setDifficulty] = useState(0.3);
  const [index, setIndex] = useState(0); const [flipped, setFlipped] = useState(false); const [reviewing, setReviewing] = useState(false); const [error, setError] = useState('');
  useEffect(() => { if (index >= dueReviews.length) setIndex(Math.max(0, dueReviews.length - 1)); }, [dueReviews.length, index]);
  const current = dueReviews[index];

  const review = async (rating: 'again' | 'hard' | 'good' | 'easy') => {
    if (!current || reviewing) return; setReviewing(true); setError('');
    try { await onReviewFlashcard(current.flashcard.flashcard_id, rating); setFlipped(false); setIndex((value) => Math.min(value, Math.max(0, dueReviews.length - 2))); }
    catch (err) { setError(err instanceof Error ? err.message : 'Review failed'); }
    finally { setReviewing(false); }
  };
  const create = async (e: React.FormEvent) => { e.preventDefault(); if (!front.trim() || !back.trim()) return; await onCreateFlashcard({ front: front.trim(), back: back.trim(), difficulty }); setFront(''); setBack(''); setShowModal(false); };

  return <div className="space-y-6">
    <div className="page-header"><div><div className="eyebrow"><BookOpenCheck className="w-4 h-4" /> LEARNING ENGINE</div><h1>Spaced repetition</h1><p>Reviews are driven by the persisted FSRS state. A card leaves this queue when its next due date moves into the future.</p></div><button className="primary-button" onClick={() => setShowModal(true)}><Plus className="w-4 h-4" /> New card</button></div>
    <div className="stats-strip"><div><span>All cards</span><strong>{flashcards.length}</strong></div><div><span>Due now</span><strong>{dueReviews.length}</strong></div><div><span>Queue position</span><strong>{dueReviews.length ? `${index + 1}/${dueReviews.length}` : '—'}</strong></div><div><span>Scheduling</span><strong>FSRS</strong></div></div>
    {error && <div className="error-banner">{error}</div>}
    {current ? <div className="review-stage">
      <div className="review-toolbar"><span><Clock3 className="w-4 h-4" /> Due review</span><span>{current.learning_state.state} · repetition {current.learning_state.repetition}</span></div>
      <button type="button" className={`flashcard ${flipped ? 'flipped' : ''}`} onClick={() => setFlipped((value) => !value)} aria-label="Flip flashcard">
        <span className="flashcard-label">{flipped ? 'ANSWER' : 'QUESTION'}</span><span className="flashcard-text">{flipped ? current.flashcard.back : current.flashcard.front}</span><span className="flashcard-hint"><RotateCw className="w-3.5 h-3.5" /> Click to flip</span>
      </button>
      {flipped && <div className="rating-grid">
        <button disabled={reviewing} className="rating-button again" onClick={() => void review('again')}><X className="w-4 h-4" /><span>Again</span><small>Reset / relearn</small></button>
        <button disabled={reviewing} className="rating-button hard" onClick={() => void review('hard')}><span>Hard</span><small>Shorter interval</small></button>
        <button disabled={reviewing} className="rating-button good" onClick={() => void review('good')}><Check className="w-4 h-4" /><span>Good</span><small>Normal interval</small></button>
        <button disabled={reviewing} className="rating-button easy" onClick={() => void review('easy')}><Flame className="w-4 h-4" /><span>Easy</span><small>Longer interval</small></button>
      </div>}
      <div className="review-nav"><button className="icon-button" disabled={index === 0} onClick={() => { setIndex((v) => v - 1); setFlipped(false); }}><ChevronLeft className="w-4 h-4" /></button><span className="muted text-xs">Review the current due queue</span><button className="icon-button" disabled={index >= dueReviews.length - 1} onClick={() => { setIndex((v) => v + 1); setFlipped(false); }}><ChevronRight className="w-4 h-4" /></button></div>
    </div> : <div className="empty-state"><BookOpenCheck className="w-8 h-8" /><h2>{flashcards.length ? 'No cards are due' : 'Your deck is empty'}</h2><p>{flashcards.length ? 'FSRS has scheduled every card for a future review. Come back when the queue is due.' : 'Create your first card or generate cards from your knowledge base.'}</p>{!flashcards.length && <button className="primary-button" onClick={() => setShowModal(true)}><Plus className="w-4 h-4" /> Create first card</button>}</div>}
    {showModal && <div className="modal-backdrop"><div className="modal-card"><div className="flex items-center justify-between"><h2>Create flashcard</h2><button className="icon-button" onClick={() => setShowModal(false)}>×</button></div><form onSubmit={create} className="space-y-4 mt-5"><label>Question<textarea required value={front} onChange={(e) => setFront(e.target.value)} rows={3} /></label><label>Answer<textarea required value={back} onChange={(e) => setBack(e.target.value)} rows={4} /></label><label>Initial difficulty<input type="number" min="0" max="1" step="0.1" value={difficulty} onChange={(e) => setDifficulty(Number(e.target.value))} /></label><div className="flex justify-end gap-2"><button type="button" className="secondary-button" onClick={() => setShowModal(false)}>Cancel</button><button className="primary-button" type="submit">Save card</button></div></form></div></div>}
  </div>;
};
