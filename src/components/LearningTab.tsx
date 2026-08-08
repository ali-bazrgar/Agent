import React, { useState } from 'react';
import { Flashcard } from '../types';
import { Layers, Plus, RotateCw, Check, X, Flame, ShieldAlert } from 'lucide-react';

interface LearningTabProps {
  flashcards: Flashcard[];
  onCreateFlashcard: (fc: { front: string; back: string; difficulty: number }) => void;
  onReviewFlashcard: (id: string, outcome: 'correct' | 'incorrect' | 'easy' | 'hard') => void;
}

export const LearningTab: React.FC<LearningTabProps> = ({
  flashcards,
  onCreateFlashcard,
  onReviewFlashcard,
}) => {
  const [showModal, setShowModal] = useState(false);
  const [front, setFront] = useState('');
  const [back, setBack] = useState('');
  const [difficulty, setDifficulty] = useState(0.5);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);

  const activeCard = flashcards[currentIndex];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!front.trim() || !back.trim()) return;
    onCreateFlashcard({ front, back, difficulty });
    setFront('');
    setBack('');
    setShowModal(false);
  };

  const handleOutcome = (outcome: 'correct' | 'incorrect' | 'easy' | 'hard') => {
    if (activeCard) {
      onReviewFlashcard(activeCard.flashcard_id, outcome);
      setIsFlipped(false);
      setCurrentIndex((prev) => (prev + 1) % flashcards.length);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center space-x-2">
            <Layers className="w-5 h-5 text-amber-600" />
            <h2 className="text-lg font-bold text-slate-900">Spaced Repetition Learning Engine</h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Flashcards & review feedback loops for agent procedural memory reinforcement.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold rounded-xl transition-colors flex items-center justify-center space-x-2 shadow-xs"
        >
          <Plus className="w-4 h-4" />
          <span>New Flashcard</span>
        </button>
      </div>

      {/* Interactive Review Deck */}
      {flashcards.length > 0 && activeCard ? (
        <div className="max-w-xl mx-auto space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-500 font-mono">
            <span>Card {currentIndex + 1} of {flashcards.length}</span>
            <span>Difficulty: {(activeCard.difficulty * 100).toFixed(0)}%</span>
          </div>

          <div
            onClick={() => setIsFlipped(!isFlipped)}
            className="cursor-pointer min-h-[220px] bg-white rounded-2xl border-2 border-slate-200 p-8 shadow-sm flex flex-col justify-between hover:border-amber-400 transition-all text-center relative group"
          >
            <div className="text-xs font-mono font-semibold uppercase tracking-wider text-amber-600">
              {isFlipped ? 'ANSWER' : 'QUESTION'}
            </div>

            <div className="text-lg font-semibold text-slate-900 py-4">
              {isFlipped ? activeCard.back : activeCard.front}
            </div>

            <div className="text-xs text-slate-400 flex items-center justify-center space-x-1">
              <RotateCw className="w-3.5 h-3.5" />
              <span>Click card to flip</span>
            </div>
          </div>

          {/* Review Controls */}
          {isFlipped && (
            <div className="grid grid-cols-4 gap-2 pt-2 animate-in fade-in duration-200">
              <button
                onClick={() => handleOutcome('incorrect')}
                className="py-2.5 bg-red-50 hover:bg-red-100 text-red-700 text-xs font-semibold rounded-xl border border-red-200 flex items-center justify-center space-x-1"
              >
                <X className="w-3.5 h-3.5" />
                <span>Hard (1d)</span>
              </button>
              <button
                onClick={() => handleOutcome('hard')}
                className="py-2.5 bg-amber-50 hover:bg-amber-100 text-amber-700 text-xs font-semibold rounded-xl border border-amber-200 flex items-center justify-center"
              >
                <span>Again (2d)</span>
              </button>
              <button
                onClick={() => handleOutcome('correct')}
                className="py-2.5 bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-semibold rounded-xl border border-blue-200 flex items-center justify-center space-x-1"
              >
                <Check className="w-3.5 h-3.5" />
                <span>Good (3d)</span>
              </button>
              <button
                onClick={() => handleOutcome('easy')}
                className="py-2.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs font-semibold rounded-xl border border-emerald-200 flex items-center justify-center space-x-1"
              >
                <Flame className="w-3.5 h-3.5" />
                <span>Easy (7d)</span>
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-white p-12 text-center rounded-2xl border border-dashed border-slate-300 space-y-3">
          <Layers className="w-8 h-8 text-slate-300 mx-auto" />
          <p className="text-sm text-slate-500 font-medium">No flashcards available in learning deck</p>
        </div>
      )}

      {/* New Flashcard Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-xl border border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-base">Create Flashcard</h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Front (Prompt / Question)</label>
                <textarea
                  required
                  rows={2}
                  value={front}
                  onChange={(e) => setFront(e.target.value)}
                  placeholder="e.g. What is the role of procedural memory?"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Back (Explanation / Answer)</label>
                <textarea
                  required
                  rows={3}
                  value={back}
                  onChange={(e) => setBack(e.target.value)}
                  placeholder="e.g. Stores explicit policy guardrails and tool call rules..."
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Initial Difficulty (0.0 - 1.0)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={difficulty}
                  onChange={(e) => setDifficulty(parseFloat(e.target.value))}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 rounded-xl text-xs font-medium hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-amber-600 text-white rounded-xl text-xs font-semibold hover:bg-amber-500 shadow-xs"
                >
                  Save Card
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
