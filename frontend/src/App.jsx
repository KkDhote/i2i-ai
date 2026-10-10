import { useEffect, useState } from "react";
import "./App.css";
const API_URL = "http://127.0.0.1:8000";

const normalizeTask = (task) => ({
  ...task,
  team: task.team || "General",
  status: task.status === "In progress" ? "In Progress" : task.status,
});

function App() {
  const [activePage, setActivePage] = useState("Overview");
  const [tasks, setTasks] = useState([]);
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState("");
  const [query, setQuery] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [taskTitle, setTaskTitle] = useState("");
  const [notice, setNotice] = useState("");
  const visibleTasks = tasks.filter((task) =>
    `${task.title} ${task.team} ${task.status}`
      .toLowerCase()
      .includes(query.toLowerCase())
  );
  
async function askAI(event) {
  event.preventDefault();

  const userQuestion = question.trim();
  if (!userQuestion) return;

  setAnswer("I2I AI is thinking...");

  try {
    const response = await fetch("http://127.0.0.1:8000/api/ai/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question: userQuestion,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.detail || "Unable to get an AI response."
      );
    }

    setAnswer(data.answer || "No answer was returned.");
    setQuestion("");
  } catch (error) {
    console.error("I2I AI error:", error);

    setAnswer(
      error.message ||
        "Unable to connect to I2I AI. Please check that the backend is running."
    );
  }
}

  useEffect(() => {
    async function loadDashboard() {
      try {
        setApiError("");
        const [tasksResponse, overviewResponse] = await Promise.all([
          fetch(`${API_URL}/api/tasks`),
          fetch(`${API_URL}/api/overview`),
        ]);
        if (!tasksResponse.ok || !overviewResponse.ok) {
          throw new Error("Failed to load dashboard");
        }
        const [tasksData, overviewData] = await Promise.all([
          tasksResponse.json(),
          overviewResponse.json(),
        ]);
        setTasks(tasksData.map(normalizeTask));
        setOverview(overviewData);
      } catch {
        setApiError("Unable to connect to the backend. Check that FastAPI is running on port 8000.");
      } finally {
        setLoading(false);
      }
    }
    loadDashboard();
  }, []);

  async function refreshOverview() {
    const response = await fetch(`${API_URL}/api/overview`);
    if (!response.ok) throw new Error("Failed to refresh overview");
    setOverview(await response.json());
  }

  async function addTask(event) {
    event.preventDefault();
    if (!taskTitle.trim()) return;
    try {
      const response = await fetch(`${API_URL}/api/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: taskTitle.trim(), description: "" }),
      });
      if (!response.ok) throw new Error("Failed to create task");
      const newTask = normalizeTask(await response.json());
      setTasks((current) => [newTask, ...current]);
      setTaskTitle("");
      setShowTaskForm(false);
      setNotice("Task added successfully.");
      try { await refreshOverview(); } catch { setApiError("Overview could not be refreshed."); }
    } catch {
      setNotice("Could not add task. Please check the backend.");
    }
  }

  async function changeStatus(id) {
    const task = tasks.find((item) => item.id === id);
    if (!task) return;
    const nextStatus = task.status === "Pending"
      ? "In Progress"
      : task.status === "In Progress" ? "Completed" : "Pending";
    try {
      const params = new URLSearchParams({ status: nextStatus });
      const response = await fetch(`${API_URL}/api/tasks/${id}?${params}`, {
        method: "PATCH",
      });
      if (!response.ok) throw new Error("Failed to update task");
      const updatedTask = normalizeTask(await response.json());
      setTasks((current) => current.map((item) =>
        item.id === id ? { ...item, ...updatedTask } : item
      ));
      setNotice("Task status updated.");
      try { await refreshOverview(); } catch { setApiError("Overview could not be refreshed."); }
    } catch {
      setNotice("Could not update task. Please check the backend.");
    }
  }

  const metrics = [
    { label: "Total tasks", value: overview?.total_tasks ?? "—", change: "Live workspace data", icon: "◈" },
    { label: "Tasks completed", value: overview?.completed_tasks ?? "—", change: "Live workspace data", icon: "✓" },
    { label: "Tasks remaining", value: overview?.pending_tasks ?? "—", change: "Includes in-progress tasks", icon: "◷" },
    { label: "Completion rate", value: overview && overview.total_tasks
      ? `${Math.round((overview.completed_tasks / overview.total_tasks) * 100)}%`
      : "0%", change: "Based on task statuses", icon: "⌘" },
  ];

  const navigation = [
    { name: "Overview", icon: "▦" },
    { name: "AI Insights", icon: "✳" },
    { name: "Workflows", icon: "⑂" },
    { name: "Tasks", icon: "☑" },
  ];
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#home" onClick={() => setActivePage("Overview")}>
          <span className="brand-mark">I</span>
          <span>
            <strong>I2I</strong>
            <small>ADAPTIVE AI PLATFORM</small>
          </span>
        </a>
        <div className="workspace-label">WORKSPACE</div>
        <div className="workspace">
          <span className="workspace-avatar">I</span>
          <span className="workspace-info">
            <strong>I2I Workspace</strong>
            <small>Free workspace</small>
          </span>
          <span className="workspace-chevron">⌄</span>
        </div>
        <div className="nav-label">MENU</div>
        <nav className="navigation">
          {navigation.map((item) => (
            <button
              key={item.name}
              className={`nav-item ${activePage === item.name ? "active" : ""}`}
              onClick={() => {
                setActivePage(item.name);
                setNotice("");
              }}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.name}
              {item.name === "AI Insights" && (
                <span className="new-tag">AI</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="upgrade-card">
            <span className="upgrade-icon">✳</span>
            <strong>Smarter decisions start here.</strong>
            <p>Turn business data into actionable insights.</p>
            <button onClick={() => setActivePage("AI Insights")}>
              Explore AI <span>→</span>
            </button>
          </div>
          <div className="profile">
            <div className="profile-avatar">I2I</div>
            <div className="profile-info">
              <strong>I2I Workspace</strong>
              <small>Team workspace</small>
            </div>
            <span className="profile-menu">•••</span>
          </div>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>Workspace</span>
            <span>/</span>
            <strong>{activePage}</strong>
          </div>
          <div className="topbar-actions">
            <label className="search-box">
              <span>⌕</span>
              <input
                aria-label="Search tasks"
                placeholder="Search tasks..."
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
              <kbd>⌘ K</kbd>
            </label>
            <button
              className="icon-button"
              aria-label="Notifications"
              onClick={() => setNotice("You're all caught up.")}
            >
              ♧<span className="notification-dot" />
            </button>
            <div className="top-avatar">HT</div>
          </div>
        </header>
        <div className="dashboard-content">
          <div className="welcome-row">
            <div>
              <div className="eyebrow">
                <span className="live-dot" /> YOUR BUSINESS AT A GLANCE
              </div>
              <h1>
                {activePage === "Overview"
                  ? "Good afternoon, team."
                  : activePage}
              </h1>
              <p className="subtitle">
                {activePage === "Overview"
                  ? "Here's what's happening across your workspace today."
                  : `Explore your ${activePage.toLowerCase()} in one place.`}
              </p>
            </div>
            <button
              className="primary-button"
              onClick={() => {
                setShowTaskForm(true);
                setNotice("");
              }}
            >
              <span>＋</span> New task
            </button>
          </div>
          {notice && (
            <div className="notice">
              <span>✓</span> {notice}
              <button onClick={() => setNotice("")}>×</button>
            </div>
          )}
          {showTaskForm && (
            <form className="task-form" onSubmit={addTask}>
              <div>
                <strong>Create a task</strong>
                <p>Add an action item to your workspace.</p>
              </div>
              <input
                autoFocus
                placeholder="e.g. Review customer feedback"
                value={taskTitle}
                onChange={(event) => setTaskTitle(event.target.value)}
                required
              />
              <button className="primary-button" type="submit">
                Add task
              </button>
              <button
                className="cancel-button"
                type="button"
                onClick={() => setShowTaskForm(false)}
              >
                Cancel
              </button>
            </form>
          )}
          {activePage === "Overview" ? (
            <>
              <section className="metrics-grid">
                {metrics.map((metric) => (
                  <article className="metric-card" key={metric.label}>
                    <div className="metric-top">
                      <span>{metric.label}</span>
                      <span className="metric-icon">{metric.icon}</span>
                    </div>
                    <div className="metric-value">{metric.value}</div>
                    <div className="metric-foot">
                      <span className="metric-change">{metric.change}</span>
                      <span>from backend</span>
                    </div>
                  </article>
                ))}
              </section>
              <section className="content-grid">
                <article className="panel performance-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Business performance</h2>
                      <p>Illustrative activity across the last 7 days</p>
                    </div>
                    <span className="period-pill">Last 7 days⌄</span>
                  </div>
                  <div className="chart-summary">
                    <div>
                      <strong>78.4%</strong>
                      <span className="metric-change"> +6.4%</span>
                    </div>
                    <span className="chart-legend">
                      <i /> Performance score
                    </span>
                  </div>
                  <div
                    className="chart"
                    role="img"
                    aria-label="Illustrative performance trend rising across seven days"
                  >
                    <div className="y-labels">
                      <span>100</span>
                      <span>75</span>
                      <span>50</span>
                      <span>25</span>
                      <span>0</span>
                    </div>
                    <div className="chart-plot">
                      <div className="grid-lines">
                        <i /><i /><i /><i /><i />
                      </div>
                      <svg
                        className="chart-svg"
                        viewBox="0 0 600 190"
                        preserveAspectRatio="none"
                        aria-hidden="true"
                      >
                        <defs>
                          <linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#7768f5" stopOpacity=".24" />
                            <stop offset="100%" stopColor="#7768f5" stopOpacity="0" />
                          </linearGradient>
                        </defs>
                        <path
                          d="M0 148 C40 138 48 110 90 122 S150 142 190 91 S250 111 290 77 S355 98 390 58 S450 86 490 43 S550 63 600 18 L600 190 L0 190 Z"
                          fill="url(#chartFill)"
                        />
                        <path
                          d="M0 148 C40 138 48 110 90 122 S150 142 190 91 S250 111 290 77 S355 98 390 58 S450 86 490 43 S550 63 600 18"
                          fill="none"
                          stroke="#7768f5"
                          strokeWidth="3"
                          vectorEffect="non-scaling-stroke"
                        />
                      </svg>
                    </div>
                  </div>
                  <div className="chart-days">
                    <span>Mon</span><span>Tue</span><span>Wed</span>
                    <span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span>
                  </div>
                  <div className="demo-note">
                    Demo visualization · Replace with live business metrics
                  </div>
                </article>
                <article className="panel ai-panel">
                  <div className="ai-heading">
                    <div className="ai-symbol">✳</div>
                    <div>
                      <h2>I2I AI</h2>
                      <p>Your business copilot</p>
                    </div>
                    <span className="beta-tag">BETA</span>
                  </div>
                  <div className="ai-intro">
                    <span className="ai-sparkle">✦</span>
                    <h3>What would you like to understand?</h3>
                    <p>
                      Ask a business question to explore how your team can
                      make smarter, data-informed decisions.
                    </p>
                  </div>
                  <div className="suggestion-label">TRY ASKING</div>
                  {[
                    "Summarize business performance",
                    "Find potential growth opportunities",
                    "What should our team prioritize?",
                  ].map((suggestion) => (
                    <button
                      className="suggestion"
                      key={suggestion}
                      onClick={() => setQuestion(suggestion)}
                    >
                      <span>✧</span> {suggestion} <span className="suggestion-arrow">↗</span>
                    </button>
                  ))}
                  
{answer && (
  <div className="ai-answer">
    <strong>I2I AI · AI-generated insight</strong>

    <div className="ai-answer-content">
      {answer === "I2I AI is thinking..." ? (
        <p className="ai-loading">
          <span className="ai-loading-dot" />
          Analyzing your workspace...
        </p>
      ) : (
        answer.split("\n").map((line, index) => {
          const cleanLine = line
            .replace(/^#{1,6}\s*/, "")
            .replace(/\*\*(.*?)\*\*/g, "$1")
            .replace(/^\s*[-*]\s+/, "• ")
            .replace(/---+/g, "")
            .trim();

          if (!cleanLine) {
            return <div key={index} className="ai-line-space" />;
          }

          return (
            <p key={index} className="ai-answer-line">
              {cleanLine}
            </p>
          );
        })
      )}
    </div>
  </div>
)}

                  <form className="ai-input" onSubmit={askAI}>
                    <input
                      aria-label="Ask I2I AI"
                      placeholder="Ask anything about your business..."
                      value={question}
                      onChange={(event) => setQuestion(event.target.value)}
                    />
                    <button type="submit" aria-label="Submit question">↑</button>
                  </form>
                  <div className="ai-disclaimer">
                    AI-powered insights · Responses based on available workspace data
                  </div>
                </article>
              </section>
              <section className="panel tasks-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Team tasks</h2>
                    <p>Keep projects moving forward</p>
                  </div>
                  <button
                    className="text-button"
                    onClick={() => setActivePage("Tasks")}
                  >
                    View all tasks →
                  </button>
                </div>
                <div className="task-table-wrap">
                  <table className="task-table">
                    <thead>
                      <tr>
                        <th>TASK</th>
                        <th>TEAM</th>
                        <th>STATUS</th>
                        <th>ACTION</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tasks.slice(0, 4).map((task) => (
                        <tr key={task.id}>
                          <td>
                            <span className="task-bullet">◇</span>
                            {task.title}
                          </td>
                          <td>{task.team}</td>
                          <td>
                            <span
                              className={`status status-${task.status
                                .toLowerCase()
                                .replace(" ", "-")}`}
                            >
                              {task.status}
                            </span>
                          </td>
                          <td>
                            <button
                              className="row-action"
                              onClick={() => changeStatus(task.id)}
                            >
                              Update
                            </button>
                          </td>
                        </tr>
                      ))}
                      {tasks.length === 0 && (
                        <tr><td colSpan="4">No tasks yet. Create your first task.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          ) : activePage === "Tasks" ? (
            <section className="panel tasks-panel">
              <div className="panel-heading">
                <div>
                  <h2>All team tasks</h2>
                  <p>Search, create, and update team action items.</p>
                </div>
              </div>
              <div className="task-table-wrap">
                <table className="task-table">
                  <thead>
                    <tr><th>TASK</th><th>TEAM</th><th>STATUS</th><th>ACTION</th></tr>
                  </thead>
                  <tbody>
                    {visibleTasks.map((task) => (
                      <tr key={task.id}>
                        <td>{task.title}</td>
                        <td>{task.team}</td>
                        <td><span className={`status status-${task.status.toLowerCase().replace(" ", "-")}`}>{task.status}</span></td>
                        <td><button className="row-action" onClick={() => changeStatus(task.id)}>Update</button></td>
                      </tr>
                    ))}
                    {visibleTasks.length === 0 && <tr><td colSpan="4">No matching tasks found.</td></tr>}
                  </tbody>
                </table>
              </div>
            </section>
          ) : (
            <section className="panel placeholder-panel">
              <div className="ai-symbol">✳</div>
              <h2>{activePage}</h2>
              <p>
                This workspace section is ready for development. We'll connect
                real workflows and AI-generated insights to the backend next.
              </p>
              <button className="primary-button" onClick={() => setActivePage("Overview")}>
                Return to overview
              </button>
            </section>
          )}
          <footer className="footer">
            <span>© 2026 I2I AI · Hackwave 3.0</span>
            <span><i className="live-dot" /> Backend connected <span className="footer-divider">·</span>Gemini AI connected · Chart uses illustrative data</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
export default App;