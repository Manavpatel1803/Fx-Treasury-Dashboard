import React, { useEffect, useState } from "react";
import {
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Bell,
  WalletCards,
  Sparkles,
} from "lucide-react";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

import { api } from "./api";

function StatCard({ title, value, subtitle }) {
  return (
    <div className="card stat-card">
      <p className="muted">{title}</p>
      <h2>{value}</h2>
      <span>{subtitle}</span>
    </div>
  );
}

function RateTable({ rates, selectedPair, onSelectPair }) {
  return (
    <div className="card">
      <div className="section-title">
        <TrendingUp size={20} />
        <h3>FX Rate Monitor</h3>
      </div>

      <div className="table">
        <div className="table-row table-head">
          <span>Pair</span>
          <span>Latest</span>
          <span>Change %</span>
          <span>Spread</span>
          <span>Status</span>
        </div>

        {rates.map((rate) => (
          <button
            key={rate.pair}
            className={`table-row clickable ${
              selectedPair === rate.pair ? "active" : ""
            }`}
            onClick={() => onSelectPair(rate.pair)}
          >
            <span>{rate.pair}</span>
            <span>{rate.latest_rate ?? "No data"}</span>

            <span
              className={
                rate.percentage_change >= 0 ? "positive" : "negative"
              }
            >
              {rate.percentage_change === null
                ? "-"
                : `${rate.percentage_change}%`}
            </span>

            <span>{rate.spread ?? "-"}</span>
            <span>{rate.status}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function HistoryChart({ pair, history }) {
  const chartData = history.map((item) => ({
    time: new Date(item.created_at).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    }),
    rate: item.rate,
  }));

  return (
    <div className="card chart-card">
      <h3>{pair} Historical Snapshots</h3>

      {chartData.length === 0 ? (
        <p className="muted">
          No history yet. Click “Collect New FX Snapshot”.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" />
            <YAxis domain={["auto", "auto"]} />
            <Tooltip />
            <Line type="monotone" dataKey="rate" strokeWidth={3} dot />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function AlertPanel({ rules, events, onCreateAlert }) {
  const [pair, setPair] = useState("GBP/USD");
  const [threshold, setThreshold] = useState(1);

  async function handleSubmit(event) {
    event.preventDefault();

    await onCreateAlert({
      pair: pair,
      threshold_percent: Number(threshold),
    });

    setThreshold(1);
  }

  return (
    <div className="card">
      <div className="section-title">
        <Bell size={20} />
        <h3>Alert Rules</h3>
      </div>

      <form className="form-inline" onSubmit={handleSubmit}>
        <input
          value={pair}
          onChange={(event) => setPair(event.target.value)}
          placeholder="GBP/USD"
        />

        <input
          value={threshold}
          onChange={(event) => setThreshold(event.target.value)}
          type="number"
          step="0.1"
          min="0.1"
          placeholder="Threshold %"
        />

        <button type="submit">Add Alert</button>
      </form>

      <h4>Active Rules</h4>

      <ul className="list">
        {rules.length === 0 && <li>No alert rules yet.</li>}

        {rules.map((rule) => (
          <li key={rule.id}>
            {rule.pair} movement over {rule.threshold_percent}%
          </li>
        ))}
      </ul>

      <h4>Recent Alert Events</h4>

      <ul className="list">
        {events.length === 0 && <li>No alerts triggered yet.</li>}

        {events.map((event) => (
          <li key={event.id}>{event.message}</li>
        ))}
      </ul>
    </div>
  );
}

function ExposurePanel({ exposures, onCreateExposure }) {
  const [form, setForm] = useState({
    business_unit: "Operations",
    currency: "INR",
    amount: 1000000,
    direction: "payable",
    description: "Supplier payment",
  });

  async function handleSubmit(event) {
    event.preventDefault();

    await onCreateExposure({
      ...form,
      amount: Number(form.amount),
    });
  }

  return (
    <div className="card">
      <div className="section-title">
        <WalletCards size={20} />
        <h3>Exposure Tracker</h3>
      </div>

      <form className="grid-form" onSubmit={handleSubmit}>
        <input
          value={form.business_unit}
          onChange={(event) =>
            setForm({ ...form, business_unit: event.target.value })
          }
          placeholder="Business unit"
        />

        <input
          value={form.currency}
          onChange={(event) =>
            setForm({ ...form, currency: event.target.value })
          }
          placeholder="Currency"
        />

        <input
          value={form.amount}
          onChange={(event) =>
            setForm({ ...form, amount: event.target.value })
          }
          type="number"
          placeholder="Amount"
        />

        <select
          value={form.direction}
          onChange={(event) =>
            setForm({ ...form, direction: event.target.value })
          }
        >
          <option value="payable">Payable</option>
          <option value="receivable">Receivable</option>
        </select>

        <input
          value={form.description}
          onChange={(event) =>
            setForm({ ...form, description: event.target.value })
          }
          placeholder="Description"
        />

        <button type="submit">Add Exposure</button>
      </form>

      <ul className="list">
        {exposures.length === 0 && <li>No exposure added yet.</li>}

        {exposures.map((exposure) => (
          <li key={exposure.id}>
            {exposure.business_unit}: {exposure.direction}{" "}
            {Number(exposure.amount).toLocaleString()} {exposure.currency} —{" "}
            {exposure.description}
          </li>
        ))}
      </ul>
    </div>
  );
}

function TreasurySummary({ summary }) {
  return (
    <div className="card">
      <h3>Treasury Summary</h3>

      <h4>FX Notes</h4>

      <ul className="list">
        {summary?.fx_notes?.map((note, index) => (
          <li key={index}>{note}</li>
        ))}
      </ul>

      <h4>Exposure Notes</h4>

      <ul className="list">
        {summary?.exposure_notes?.length === 0 && (
          <li>No exposures added yet.</li>
        )}

        {summary?.exposure_notes?.map((note, index) => (
          <li key={index}>{note}</li>
        ))}
      </ul>

      <h4>Alert Notes</h4>

      <ul className="list">
        {summary?.alerts?.length === 0 && <li>No alert events yet.</li>}

        {summary?.alerts?.map((note, index) => (
          <li key={index}>{note}</li>
        ))}
      </ul>
    </div>
  );
}
function LiveRatesPanel({ liveRates }) {
  return (
    <div className="card live-rates-card">
      <div className="section-title">
        <h3>Live Currency Rates</h3>
      </div>

      <p className="muted">
        Auto-refreshing live FX rates from backend.
      </p>

      <div className="live-rates-grid">
        {liveRates.length === 0 && (
          <p className="muted">Loading live currency rates...</p>
        )}

        {liveRates.map((item) => (
          <div className="live-rate-box" key={item.pair}>
            <p className="live-pair">{item.pair}</p>

            <h2>{item.rate}</h2>

            <div className="live-rate-details">
              <span>Bid: {item.bid_rate}</span>
              <span>Ask: {item.ask_rate}</span>
              <span>Spread: {item.spread}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function WhyItMoved({ pair, explanation, loading, onExplain }) {
  const change = explanation?.move_percent;
  const isUp = explanation?.direction === "up";
  const isDown = explanation?.direction === "down";

  return (
    <div className="card why-card">
      <div className="section-title">
        <Sparkles size={20} />
        <h3>Why did {pair} move?</h3>
      </div>

      <button
        className="why-button"
        onClick={() => onExplain(pair)}
        disabled={loading}
      >
        {loading ? "Analysing news…" : `Explain ${pair}`}
      </button>

      {explanation && (
        <div className="why-body">
          <div className="why-headline">
            {isUp && <TrendingUp size={18} className="positive" />}
            {isDown && <TrendingDown size={18} className="negative" />}
            <span
              className={
                isUp ? "positive" : isDown ? "negative" : "muted"
              }
            >
              {change === null || change === undefined
                ? "Little movement"
                : `${change > 0 ? "+" : ""}${change}%`}
            </span>
            {explanation.cached && <span className="badge">cached</span>}
          </div>

          <p className="why-text">{explanation.explanation}</p>

          {explanation.sources?.length > 0 && (
            <details className="why-sources">
              <summary>Sources ({explanation.sources.length})</summary>
              <ul className="list">
                {explanation.sources.map((s, i) => (
                  <li key={i}>
                    <a href={s.url} target="_blank" rel="noreferrer">
                      {s.title}
                    </a>{" "}
                    <span className="muted">— {s.source}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}

          <p className="disclaimer muted">
            Educational context grounded in recent news — not financial advice.
          </p>
        </div>
      )}
    </div>
  );
}

function App() {
  const [rates, setRates] = useState([]);
  const [selectedPair, setSelectedPair] = useState("GBP/USD");
  const [history, setHistory] = useState([]);
  const [summary, setSummary] = useState(null);
  const [alertRules, setAlertRules] = useState([]);
  const [alertEvents, setAlertEvents] = useState([]);
  const [exposures, setExposures] = useState([]);
  const [loading, setLoading] = useState(false);
  const [liveRates, setLiveRates] = useState([]);
  const [explanation, setExplanation] = useState(null);
  const [explaining, setExplaining] = useState(false);

  async function loadDashboard(pair = selectedPair) {
    const [
      latestRates,
      historyRows,
      treasurySummary,
      rules,
      events,
      exposureRows,
    ] = await Promise.all([
      api.getLatestRates(),
      api.getHistory(pair),
      api.getTreasurySummary(),
      api.getAlertRules(),
      api.getAlertEvents(),
      api.getExposures(),
    ]);

    setRates(latestRates);
    setHistory(historyRows);
    setSummary(treasurySummary);
    setAlertRules(rules);
    setAlertEvents(events);
    setExposures(exposureRows);
  }
  async function loadLiveRates() {
  try {
    const liveData = await api.getLiveRates();
    setLiveRates(liveData);
  } catch (error) {
    console.error("Failed to load live rates:", error);
  }
}

async function collectSnapshot() {
  setLoading(true);

  try {
    await api.createAllSnapshots();
    await loadDashboard();
  } catch (error) {
    alert(error.message);
    console.error("Snapshot error:", error);
  } finally {
    setLoading(false);
  }
}

  async function handlePairChange(pair) {
    setSelectedPair(pair);
    setExplanation(null);

    try {
      const historyRows = await api.getHistory(pair);
      setHistory(historyRows);
    } catch (error) {
      console.error(error);
    }
  }

  async function explainPair(pair) {
    setExplaining(true);

    try {
      const result = await api.getExplanation(pair);
      setExplanation(result);
    } catch (error) {
      console.error("Explain error:", error);
      alert("Could not fetch explanation.");
    } finally {
      setExplaining(false);
    }
  }

  async function createAlert(payload) {
    try {
      await api.createAlert(payload);
      await loadDashboard();
    } catch (error) {
      alert("Failed to create alert rule.");
      console.error(error);
    }
  }

  async function createExposure(payload) {
    try {
      await api.createExposure(payload);
      await loadDashboard();
    } catch (error) {
      alert("Failed to create exposure.");
      console.error(error);
    }
  }

  useEffect(() => {
    // Load the main dashboard data on mount.
    loadDashboard().catch((error) => {
      console.error(error);
    });

    // Load live rates now, then refresh them every 30s.
    loadLiveRates();
    const intervalId = setInterval(() => {
      loadLiveRates();
    }, 30000);

    return () => clearInterval(intervalId);
  }, []);

  const activeAlerts = alertEvents.length;

  const latestRateCount = rates.filter(
    (rate) => rate.latest_rate !== null
  ).length;

  const latestSelected = rates.find((rate) => rate.pair === selectedPair);

  return (
    <main>
      <header className="hero">
        <div>
          <p className="eyebrow">FinTech Treasury System</p>
          <h1>FX Rate Monitor & Treasury Dashboard</h1>
          <p>
            Track FX pairs, store rate snapshots, monitor movements, manage
            exposure, and generate treasury-style business summaries.
          </p>
        </div>

        <button onClick={collectSnapshot} disabled={loading}>
          <RefreshCw size={18} />
          {loading ? "Collecting..." : "Collect New FX Snapshot"}
        </button>
      </header>

      <section className="stats">
        <StatCard
          title="Tracked Pairs"
          value={rates.length || 4}
          subtitle="GBP/USD, EUR/USD, USD/INR, EUR/GBP"
        />

        <StatCard
          title="Pairs With Data"
          value={latestRateCount}
          subtitle="Saved in SQL database"
        />

        <StatCard
          title="Selected Change"
          value={
            latestSelected?.percentage_change === null ||
            latestSelected?.percentage_change === undefined
              ? "-"
              : `${latestSelected.percentage_change}%`
          }
          subtitle={selectedPair}
        />

        <StatCard
          title="Alert Events"
          value={activeAlerts}
          subtitle="Recent threshold breaches"
        />
      </section>

      <section className="dashboard-grid">
        <RateTable
          rates={rates}
          selectedPair={selectedPair}
          onSelectPair={handlePairChange}
        />

        <HistoryChart pair={selectedPair} history={history} />
      </section>

      <section className="dashboard-grid">
        <WhyItMoved
          pair={selectedPair}
          explanation={explanation}
          loading={explaining}
          onExplain={explainPair}
        />
      </section>

      <section className="dashboard-grid">
        <AlertPanel
          rules={alertRules}
          events={alertEvents}
          onCreateAlert={createAlert}
        />

        <ExposurePanel
          exposures={exposures}
          onCreateExposure={createExposure}
        />
      </section>

      <TreasurySummary summary={summary} />
      <LiveRatesPanel liveRates={liveRates} />
    </main>
  );
}


export default App;