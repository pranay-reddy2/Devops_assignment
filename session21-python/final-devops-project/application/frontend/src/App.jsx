import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from './api.js';

const CATEGORY_COLORS = {
  FOOD: '#f59e0b', TRANSPORT: '#3b82f6', RENT: '#8b5cf6', BILLS: '#ef4444', SHOPPING: '#ec4899',
  HEALTH: '#10b981', ENTERTAINMENT: '#f97316', EDUCATION: '#06b6d4', OTHER: '#64748b',
};
const today = () => new Date().toISOString().slice(0, 10);
const emptyForm = { title: '', amount: '', category: 'FOOD', spent_on: today(), note: '' };

function money(value, currency = 'INR') {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency, maximumFractionDigits: 2 }).format(Number(value || 0));
}

function Kpi({ label, value, hint }) {
  return (
    <div className="kpi">
      <span className="kpi-label">{label}</span>
      <strong className="kpi-value">{value}</strong>
      {hint && <span className="kpi-hint">{hint}</span>}
    </div>
  );
}

function CategoryBreakdown({ summary }) {
  const max = Math.max(...summary.by_category.map((c) => Number(c.total)), 1);
  return (
    <section className="card">
      <h2>Spending by category</h2>
      {summary.by_category.length === 0 && <p className="muted">No expenses yet.</p>}
      <ul className="bars">
        {summary.by_category.map((c) => (
          <li key={c.category}>
            <span className="bar-label">{c.category.toLowerCase()}</span>
            <span className="bar-track">
              <span className="bar-fill" style={{ width: `${(Number(c.total) / max) * 100}%`, background: CATEGORY_COLORS[c.category] }} />
            </span>
            <span className="bar-value">{money(c.total, summary.currency)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ExpenseForm({ categories, onCreated }) {
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await api.create({ ...form, amount: form.amount });
      setForm({ ...emptyForm, category: form.category });
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="card">
      <h2>Add expense</h2>
      <form className="form" onSubmit={submit}>
        <input placeholder="What did you spend on?" value={form.title} onChange={set('title')} required maxLength={120} />
        <div className="row">
          <input type="number" step="0.01" min="0.01" placeholder="Amount" value={form.amount} onChange={set('amount')} required />
          <select value={form.category} onChange={set('category')}>
            {categories.map((c) => <option key={c} value={c}>{c.toLowerCase()}</option>)}
          </select>
          <input type="date" value={form.spent_on} onChange={set('spent_on')} required />
        </div>
        <input placeholder="Note (optional)" value={form.note} onChange={set('note')} maxLength={500} />
        {error && <p className="error">{error}</p>}
        <button disabled={saving}>{saving ? 'Saving…' : 'Add expense'}</button>
      </form>
    </section>
  );
}

export default function App() {
  const [categories, setCategories] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [summary, setSummary] = useState(null);
  const [filter, setFilter] = useState('');
  const [status, setStatus] = useState('loading');

  const load = useCallback(async () => {
    try {
      const [list, sum] = await Promise.all([api.list({ category: filter }), api.summary()]);
      setExpenses(list);
      setSummary(sum);
      setStatus('ok');
    } catch {
      setStatus('error');
    }
  }, [filter]);

  useEffect(() => { api.categories().then(setCategories).catch(() => setStatus('error')); }, []);
  useEffect(() => { load(); }, [load]);

  async function remove(id) {
    await api.remove(id);
    load();
  }

  const currency = summary?.currency || 'INR';
  const average = useMemo(
    () => (summary && summary.count ? Number(summary.total) / summary.count : 0),
    [summary],
  );

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">₹ SpendWise</div>
        <nav>
          <a className="active">Dashboard</a>
          <a>Expenses</a>
          <a>Reports</a>
        </nav>
        <div className={`api-status ${status}`}>
          <span className="dot" /> API {status === 'ok' ? 'connected' : status === 'loading' ? 'connecting…' : 'unreachable'}
        </div>
      </aside>

      <main>
        <header className="header">
          <div>
            <h1>Personal expenses</h1>
            <p className="muted">Track where the money goes, by category and month.</p>
          </div>
        </header>

        {status === 'error' && (
          <div className="banner">Cannot reach the SpendWise API. Is the backend running and is /api routed to it?</div>
        )}

        {summary && (
          <section className="kpis">
            <Kpi label="This month" value={money(summary.this_month, currency)} />
            <Kpi label="All time" value={money(summary.total, currency)} hint={`${summary.count} expenses`} />
            <Kpi label="Average expense" value={money(average, currency)} />
            <Kpi label="Top category" value={summary.top_category ? summary.top_category.toLowerCase() : '—'} />
          </section>
        )}

        <div className="grid">
          <ExpenseForm categories={categories} onCreated={load} />
          {summary && <CategoryBreakdown summary={summary} />}
        </div>

        <section className="card">
          <div className="table-head">
            <h2>Expenses</h2>
            <select value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="">All categories</option>
              {categories.map((c) => <option key={c} value={c}>{c.toLowerCase()}</option>)}
            </select>
          </div>
          <table>
            <thead>
              <tr><th>Date</th><th>Title</th><th>Category</th><th className="num">Amount</th><th /></tr>
            </thead>
            <tbody>
              {expenses.map((e) => (
                <tr key={e.id}>
                  <td>{e.spent_on}</td>
                  <td>{e.title}{e.note && <span className="note">{e.note}</span>}</td>
                  <td><span className="badge" style={{ background: CATEGORY_COLORS[e.category] }}>{e.category.toLowerCase()}</span></td>
                  <td className="num">{money(e.amount, currency)}</td>
                  <td><button className="link" onClick={() => remove(e.id)} aria-label={`Delete ${e.title}`}>Delete</button></td>
                </tr>
              ))}
              {expenses.length === 0 && (
                <tr><td colSpan={5} className="muted">No expenses{filter && ' in this category'}.</td></tr>
              )}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  );
}
