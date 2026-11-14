import React, { useState, useEffect } from 'react';
import { Brain, Plus, Trash2, Search, CheckCircle, Tag } from 'lucide-react';

interface MemoryEntity {
  id: string;
  key_name: string;
  category: string;
  value_data: { text?: string } | any;
  confidence_score: number;
  provenance: string;
}

export const MemoryExplorer: React.FC = () => {
  const [entities, setEntities] = useState<MemoryEntity[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);

  // Form State
  const [newKey, setNewKey] = useState('');
  const [newCategory, setNewCategory] = useState('preference');
  const [newValue, setNewValue] = useState('');

  const categories = [
    { id: 'all', label: 'All Memories' },
    { id: 'academic', label: 'Academic' },
    { id: 'project', label: 'Projects' },
    { id: 'preference', label: 'Preferences' },
    { id: 'work', label: 'Work' },
    { id: 'decision', label: 'Decisions' },
  ];

  const fetchEntities = async () => {
    try {
      setLoading(true);
      const url = selectedCategory === 'all' 
        ? '/api/memory/entities' 
        : `/api/memory/entities?category=${selectedCategory}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setEntities(data);
      }
    } catch (e) {
      console.error('Failed to load memory entities:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntities();
  }, [selectedCategory]);

  const handleAddMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKey.trim() || !newValue.trim()) return;

    try {
      const res = await fetch('/api/memory/entities', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          key_name: newKey.trim(),
          category: newCategory,
          value_data: { text: newValue.trim() },
          confidence_score: 1.0,
          provenance: 'user_explicit'
        })
      });

      if (res.ok) {
        setNewKey('');
        setNewValue('');
        setShowAddModal(false);
        fetchEntities();
      }
    } catch (e) {
      console.error('Failed to save memory:', e);
    }
  };

  const handleDeleteMemory = async (id: string) => {
    try {
      const res = await fetch(`/api/memory/entities/${id}`, { method: 'DELETE' });
      if (res.ok) {
        setEntities((prev) => prev.filter((item) => item.id !== id));
      }
    } catch (e) {
      console.error('Failed to delete memory:', e);
    }
  };

  const filteredEntities = entities.filter((e) => {
    const q = searchQuery.toLowerCase();
    const keyMatch = e.key_name.toLowerCase().includes(q);
    const textVal = typeof e.value_data === 'string' 
      ? e.value_data 
      : (e.value_data?.text || JSON.stringify(e.value_data));
    const valMatch = textVal.toLowerCase().includes(q);
    return keyMatch || valMatch;
  });

  return (
    <div className="flex flex-col h-full bg-[#040e21]/60 border border-cyan-500/20 rounded-2xl p-6 backdrop-blur-md hud-glow overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-cyan-500/20 pb-4 mb-4">
        <div className="flex items-center space-x-2.5">
          <Brain className="w-5 h-5 text-cyan-400" />
          <h2 className="font-hud font-bold text-sm tracking-wider text-cyan-300">
            PERSONAL MEMORY & KNOWLEDGE MATRIX
          </h2>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="bg-cyan-600 hover:bg-cyan-500 text-white px-3.5 py-1.5 rounded-lg text-xs font-hud font-semibold flex items-center space-x-1.5 shadow-md shadow-cyan-600/30 transition"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>REMEMBER NEW FACT</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        {/* Category Pills */}
        <div className="flex flex-wrap gap-1.5">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`text-xs px-3 py-1 rounded-full border transition ${
                selectedCategory === cat.id
                  ? 'bg-cyan-950 border-cyan-400 text-cyan-300 shadow-[0_0_8px_rgba(6,182,212,0.3)]'
                  : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative min-w-[220px]">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search memory..."
            className="w-full bg-[#020617] border border-cyan-900/60 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400 transition"
          />
        </div>
      </div>

      {/* Memory Cards Grid */}
      <div className="flex-1 overflow-y-auto pr-1">
        {loading ? (
          <div className="h-full flex items-center justify-center text-cyan-400 font-hud text-xs animate-pulse">
            RETRIEVING MEMORY ENTITIES...
          </div>
        ) : filteredEntities.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-500 space-y-2">
            <Brain className="w-10 h-10 text-cyan-500/20" />
            <p className="text-xs">No stored memories found for this filter.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {filteredEntities.map((entity) => {
              const displayVal = typeof entity.value_data === 'string'
                ? entity.value_data
                : (entity.value_data?.text || JSON.stringify(entity.value_data));

              return (
                <div
                  key={entity.id}
                  className="bg-[#081226] border border-cyan-900/40 hover:border-cyan-500/40 rounded-xl p-4 flex flex-col justify-between transition-all group shadow-sm hover:shadow-cyan-950"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-mono uppercase bg-cyan-950/80 text-cyan-400 border border-cyan-800/40 px-2 py-0.5 rounded flex items-center gap-1">
                        <Tag className="w-2.5 h-2.5" />
                        {entity.category}
                      </span>
                      <button
                        onClick={() => handleDeleteMemory(entity.id)}
                        className="text-slate-500 hover:text-rose-400 p-1 transition opacity-0 group-hover:opacity-100"
                        title="Forget this memory"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <h3 className="font-hud text-xs font-semibold text-slate-200 mb-1">
                      {entity.key_name.replace(/_/g, ' ')}
                    </h3>
                    <p className="text-xs text-slate-400 leading-relaxed font-medium">
                      {displayVal}
                    </p>
                  </div>

                  <div className="mt-3 pt-2.5 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500">
                    <span className="flex items-center gap-1 text-emerald-400 font-mono">
                      <CheckCircle className="w-3 h-3" />
                      {Math.round(entity.confidence_score * 100)}% Verified
                    </span>
                    <span className="capitalize">{entity.provenance.replace('_', ' ')}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Add Fact Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[#040e21] border border-cyan-500/40 rounded-2xl p-6 max-w-md w-full hud-glow">
            <h3 className="font-hud font-bold text-sm text-cyan-300 mb-4 flex items-center gap-2">
              <Brain className="w-4 h-4 text-cyan-400" />
              <span>RECORD NEW MEMORY FACT</span>
            </h3>

            <form onSubmit={handleAddMemory} className="space-y-4">
              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">Key Name (Identifier)</label>
                <input
                  type="text"
                  value={newKey}
                  onChange={(e) => setNewKey(e.target.value)}
                  placeholder="e.g. preferred_editor, upcoming_exam"
                  className="w-full bg-[#020617] border border-cyan-900 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-cyan-400"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">Category</label>
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  className="w-full bg-[#020617] border border-cyan-900 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-cyan-400"
                >
                  <option value="preference">Preference</option>
                  <option value="academic">Academic</option>
                  <option value="project">Project</option>
                  <option value="work">Work</option>
                  <option value="decision">Decision</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">Fact / Value Details</label>
                <textarea
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  placeholder="e.g. Computer Networks examination on Tuesday 10:00 AM"
                  rows={3}
                  className="w-full bg-[#020617] border border-cyan-900 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-cyan-400"
                  required
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-lg text-xs text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-cyan-600 hover:bg-cyan-500 text-white px-4 py-2 rounded-lg text-xs font-hud font-semibold shadow-md shadow-cyan-600/30"
                >
                  SAVE FACT
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
