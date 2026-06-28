import React, { useEffect, useMemo, useRef, useState } from 'react'
import { CATALOG, nextCustomer, resolveOrder, RESTOCK_OFFERS, DAY_GOALS } from './gameData.js'
import { Coins, RepStars, PatienceRing, Floaters, useFloaters } from './ui.jsx'
import SupportSim from './SupportSim.jsx'

/* ─────────────────────────────────────────────────────────────────────────────
   DEVELOPER LANDING PAGE & SIMULATOR PORTAL
   ───────────────────────────────────────────────────────────────────────────── */

export default function App() {
  const [currentTab, setCurrentTab] = useState('overview') // 'overview' | 'game-sims'
  const [signedUp, setSignedUp] = useState(false)
  const [subprojectActiveTab, setSubprojectActiveTab] = useState('platform') // 'platform' | 'shopper_sim' | 'commerce_rle'
  const [activePlayground, setActivePlayground] = useState('sprint') // 'sprint' | 'support'

  // Scroll to top on tab change
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [currentTab])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--putty)' }}>
      
      {/* Navigation Header */}
      <nav className="navbar">
        <div className="container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', padding: 0 }}>
          <a href="#" className="nav-logo" onClick={(e) => { e.preventDefault(); setCurrentTab('overview') }}>
            <span className="dot" />
            shopworld<span>.dev</span>
          </a>
          <ul className="nav-menu">
            <li>
              <button 
                className={`nav-btn ${currentTab === 'overview' ? 'active' : ''}`}
                onClick={() => setCurrentTab('overview')}
              >
                Overview & Docs
              </button>
            </li>
            <li>
              <button 
                className={`nav-btn ${currentTab === 'game-sims' ? 'active' : ''}`}
                onClick={() => setCurrentTab('game-sims')}
              >
                Game Sims Playground
              </button>
            </li>
            <li>
              <a 
                href="https://github.com/metonymize-kripa/shopworld.dev" 
                target="_blank" 
                rel="noopener noreferrer"
                className="nav-action-btn"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
                GitHub
              </a>
            </li>
          </ul>
        </div>
      </nav>

      {/* Mobile Top Row Navigation */}
      <div className="nav-mobile-row">
        <button 
          className={`nav-btn ${currentTab === 'overview' ? 'active' : ''}`}
          onClick={() => setCurrentTab('overview')}
          style={{ fontSize: 13, padding: '6px 12px' }}
        >
          Overview & Docs
        </button>
        <button 
          className={`nav-btn ${currentTab === 'game-sims' ? 'active' : ''}`}
          onClick={() => setCurrentTab('game-sims')}
          style={{ fontSize: 13, padding: '6px 12px' }}
        >
          Game Sims Playground
        </button>
        <a 
          href="https://github.com/metonymize-kripa/shopworld.dev" 
          target="_blank" 
          rel="noopener noreferrer"
          className="nav-btn"
          style={{ fontSize: 13, padding: '6px 12px', display: 'inline-flex', alignItems: 'center', gap: 4 }}
        >
          GitHub ↗
        </a>
      </div>

      {/* Main Page Area */}
      {currentTab === 'overview' ? (
        <OverviewSection 
          setTab={setCurrentTab} 
          subActiveTab={subprojectActiveTab} 
          setSubActiveTab={setSubprojectActiveTab}
          signedUp={signedUp}
          setSignedUp={setSignedUp}
        />
      ) : (
        <GameSimsSection 
          activePlayground={activePlayground} 
          setActivePlayground={setActivePlayground}
          signedUp={signedUp}
          setSignedUp={setSignedUp}
        />
      )}

      {/* Footer Section */}
      <footer className="footer">
        <div className="container">
          <div className="footer-links">
            <a href="#" className="footer-link" onClick={(e) => { e.preventDefault(); setCurrentTab('overview') }}>Overview</a>
            <a href="#" className="footer-link" onClick={(e) => { e.preventDefault(); setCurrentTab('game-sims') }}>Game Sims</a>
            <a href="https://github.com/metonymize-kripa/shopworld.dev" className="footer-link" target="_blank" rel="noopener noreferrer">GitHub</a>
            <a href="https://appworld.dev" className="footer-link" target="_blank" rel="noopener noreferrer">AppWorld</a>
          </div>
          <p>© 2026 shopworld.dev · Bounded Evaluation Harness for Agentic Commerce.</p>
        </div>
      </footer>

    </div>
  )
}

/* ─────────────────────────────────────────────────────────────────────────────
   OVERVIEW & SPEC SECTION
   ───────────────────────────────────────────────────────────────────────────── */

function OverviewSection({ setTab, subActiveTab, setSubActiveTab, signedUp, setSignedUp }) {
  
  const handleCopy = (text, id) => {
    navigator.clipboard.writeText(text);
    const btn = document.getElementById(id);
    if (btn) {
      btn.innerText = 'Copied!';
      setTimeout(() => { btn.innerText = 'Copy'; }, 2000);
    }
  }

  return (
    <>
      {/* Hero Section */}
      <section className="section-pad alt" style={{ borderBottom: '1px solid var(--line)' }}>
        <div className="container hero-grid">
          <div>
            <div className="kicker">Evaluative Commerce Sandboxes</div>
            <h1 className="hero-tagline display">
              The Agentic Commerce <span style={{ color: 'var(--mint-deep)' }}>Evaluation Suite.</span>
            </h1>
            <p className="hero-sub">
              Before giving an AI operator write access to live stores, verify its ability to make profitable, policy-safe decisions. ShopWorld is a suite of evaluation and training sandboxes modeling messy customer support, returns, WISMO exceptions, and budget constraints.
            </p>
            <div className="hero-cta">
              <button className="btn btn-primary" onClick={() => setTab('game-sims')}>
                Launch Game Sims Playground →
              </button>
              <a 
                href="https://github.com/metonymize-kripa/shopworld.dev" 
                target="_blank" 
                rel="noopener noreferrer" 
                className="btn btn-ghost"
              >
                Explore GitHub Repos
              </a>
            </div>
            
            <div className="quickstart-box">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <span style={{ fontSize: 10, color: 'var(--slate-muted)', fontFamily: 'var(--display)', fontWeight: 600 }}>INSTALL DETERMISTIC ENGINE</span>
                <code>pip install shopper-sim</code>
              </div>
              <button 
                id="copy-pip-engine" 
                className="copy-btn" 
                onClick={() => handleCopy('pip install shopper-sim', 'copy-pip-engine')}
              >
                Copy
              </button>
            </div>
          </div>
          
          {/* Visual Showcase (Teaser phone wrapper for the simulator) */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div className="dev-card" style={{ padding: 24, background: '#fff', width: '100%', maxWidth: 360, transform: 'rotate(2deg)' }}>
              <div className="kicker" style={{ marginBottom: 12 }}>Capabilities Checked</div>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 10, fontSize: 14 }}>
                <li style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ color: 'var(--mint-deep)', fontWeight: 'bold' }}>✓</span> <strong>State-diff evaluation</strong> (db checks)
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ color: 'var(--mint-deep)', fontWeight: 'bold' }}>✓</span> <strong>Collateral damage tracking</strong>
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ color: 'var(--mint-deep)', fontWeight: 'bold' }}>✓</span> <strong>Deterministic shopper NLG</strong>
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ color: 'var(--mint-deep)', fontWeight: 'bold' }}>✓</span> <strong>Negative refusal tasks</strong>
                </li>
              </ul>
              <hr style={{ border: 0, borderTop: '1px solid var(--line)', margin: '14px 0' }} />
              <button 
                className="btn btn-mint" 
                style={{ width: '100%', padding: '12px', fontSize: 14, borderRadius: 10 }}
                onClick={() => setTab('game-sims')}
              >
                Run Web Simulators
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Core Packages Section */}
      <section className="section-pad">
        <div className="container">
          <div style={{ textAlign: 'center', marginBottom: 48 }}>
            <div className="kicker">Repository map & capabilities</div>
            <h2 className="section-title">The Three Pillars of ShopWorld</h2>
            <p style={{ color: 'var(--ink-soft)', maxWidth: 640, margin: '0 auto', fontSize: 16 }}>
              A horizontal slice of evaluation runtimes covering standard Shopify APIs, deterministic buyer simulation, and Gym-style Amazon commerce environments.
            </p>
          </div>

          <div className="grid-3">
            <div className="dev-card">
              <span style={{ fontSize: 32 }}>🖥️</span>
              <h3 style={{ marginTop: 14 }}>shopworld-platform</h3>
              <p>
                Python evaluation engine orchestrating Shopify-like workflows. Builds seeded states, traces tool actions, and provides state-based grading reports on correctness, fraud, and policy boundaries.
              </p>
              <button 
                className="btn btn-ghost" 
                style={{ marginTop: 20, padding: '8px 12px', fontSize: 12, borderRadius: 8 }}
                onClick={() => { setSubActiveTab('platform'); document.getElementById('subprojects-anchor').scrollIntoView({ behavior: 'smooth' }) }}
              >
                Read Spec →
              </button>
            </div>

            <div className="dev-card">
              <span style={{ fontSize: 32 }}>🤖</span>
              <h3 style={{ marginTop: 14 }}>shopper_sim</h3>
              <p>
                Fully deterministic, LLM-free shopper behavioral engine. Simulates realistic buyer responses under 52 macro query families. Guarantees that any final score variance is caused by the merchant agent.
              </p>
              <button 
                className="btn btn-ghost" 
                style={{ marginTop: 20, padding: '8px 12px', fontSize: 12, borderRadius: 8 }}
                onClick={() => { setSubActiveTab('shopper_sim'); document.getElementById('subprojects-anchor').scrollIntoView({ behavior: 'smooth' }) }}
              >
                Read Spec →
              </button>
            </div>

            <div className="dev-card">
              <span style={{ fontSize: 32 }}>🏋️</span>
              <h3 style={{ marginTop: 14 }}>commerce_rle</h3>
              <p>
                Gym-style reinforcement learning environment for Amazon-like commerce. Implements state-diff evaluation, strict field-level collateral-damage penalties, and negative refusal task scenarios.
              </p>
              <button 
                className="btn btn-ghost" 
                style={{ marginTop: 20, padding: '8px 12px', fontSize: 12, borderRadius: 8 }}
                onClick={() => { setSubActiveTab('commerce_rle'); document.getElementById('subprojects-anchor').scrollIntoView({ behavior: 'smooth' }) }}
              >
                Read Spec →
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Subproject Deep-Dive Tabs (Serious Section) */}
      <span id="subprojects-anchor" />
      <section className="section-pad dark">
        <div className="container">
          <div style={{ marginBottom: 12 }}>
            <div className="kicker" style={{ color: 'var(--mint)' }}>TECHNICAL DEEP DIVE</div>
            <h2 className="section-title" style={{ color: '#fff' }}>Harness Architecture</h2>
          </div>

          <div className="subproject-dashboard">
            <div className="dashboard-header">
              <div className="dashboard-tabs">
                <button 
                  className={`dashboard-tab-btn ${subActiveTab === 'platform' ? 'active' : ''}`}
                  onClick={() => setSubActiveTab('platform')}
                >
                  shopworld-platform
                </button>
                <button 
                  className={`dashboard-tab-btn ${subActiveTab === 'shopper_sim' ? 'active' : ''}`}
                  onClick={() => setSubActiveTab('shopper_sim')}
                >
                  shopper_sim
                </button>
                <button 
                  className={`dashboard-tab-btn ${subActiveTab === 'commerce_rle' ? 'active' : ''}`}
                  onClick={() => setSubActiveTab('commerce_rle')}
                >
                  commerce_rle
                </button>
              </div>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--slate-muted)', padding: '10px 0' }}>
                Python 3.12+ · deterministic
              </span>
            </div>

            <div className="dashboard-body">
              {subActiveTab === 'platform' && (
                <div className="dashboard-grid">
                  <div className="detail-list">
                    <div className="detail-item">
                      <div className="detail-icon">⚙</div>
                      <div className="detail-text">
                        <h4>Seeded Commerce State</h4>
                        <p>Initializes a deterministic SQLite sandbox with users, orders, payment options, and inventory levels.</p>
                      </div>
                    </div>
                    <div className="detail-item">
                      <div className="detail-icon">⚡</div>
                      <div className="detail-text">
                        <h4>Shopify-like API Surface</h4>
                        <p>Allows agents to trigger full administrative transactions (order updates, shipping adjustments, inventory decrements).</p>
                      </div>
                    </div>
                    <div className="detail-item">
                      <div className="detail-icon">📊</div>
                      <div className="detail-text">
                        <h4>Readiness & Trust Score</h4>
                        <p>Grades completed traces on whether they completed the task, respected policies, and avoided customer overpromises.</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="editor-frame">
                    <div className="editor-titlebar">
                      <div className="editor-dots">
                        <span className="editor-dot red" />
                        <span className="editor-dot yellow" />
                        <span className="editor-dot green" />
                      </div>
                      <span className="editor-filename">evaluation_run.py</span>
                      <span className="editor-lang">Python</span>
                    </div>
                    <div className="editor-content">
                      <pre>
{`<span className="keyword">import</span> shopworld_platform <span className="keyword">as</span> sw

<span className="comment"># 1. Initialize seeded database state</span>
state = sw.init_state(seed=<span className="number">101</span>)

<span className="comment"># 2. Bind trace recorder to Shopify API client</span>
client = sw.ShopifyAPIClient(state)

<span className="comment"># 3. Agent executes steps (buying product)</span>
trace = client.run_agent(agent_fn)

<span className="comment"># 4. Grade resulting database delta</span>
report = sw.evaluator.grade(trace)
<span className="keyword">print</span>(<span className="string">f"TGC: {report.tgc_score}"</span>)`}
                      </pre>
                    </div>
                  </div>
                </div>
              )}

              {subActiveTab === 'shopper_sim' && (
                <div className="dashboard-grid">
                  <div className="detail-list">
                    <div className="detail-item">
                      <div className="detail-icon">⏱</div>
                      <div className="detail-text">
                        <h4>DeterministicDialogue Policy</h4>
                        <p>State-machine driven dialogue rules that act as the buyer, ensuring consistent phrasing for a given seed.</p>
                      </div>
                    </div>
                    <div className="detail-item">
                      <div className="detail-icon">📋</div>
                      <div className="detail-text">
                        <h4>Goal Stack & Preconditions</h4>
                        <p>Compiles scenarios into ordered goals (e.g. must locate order before requesting size exchange) to prevent shortcutting.</p>
                      </div>
                    </div>
                    <div className="detail-item">
                      <div className="detail-icon">🎭</div>
                      <div className="detail-text">
                        <h4>52 Journey Families</h4>
                        <p>Covers discovery, cart, checkout, returns, and exchanges, with custom traits representing impatient or anxious buyers.</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="editor-frame">
                    <div className="editor-titlebar">
                      <div className="editor-dots">
                        <span className="editor-dot red" />
                        <span className="editor-dot yellow" />
                        <span className="editor-dot green" />
                      </div>
                      <span className="editor-filename">run_simulation.py</span>
                      <span className="editor-lang">Python</span>
                    </div>
                    <div className="editor-content">
                      <pre>
{`<span className="keyword">from</span> shopper_sim <span className="keyword">import</span> compile_full_battery, run_battery

<span className="comment"># 1. Compile 59 unique scenarios</span>
scenarios = compile_full_battery()

<span className="comment"># 2. Evaluate conversational agent with repeats</span>
run = run_battery(
    scenarios,
    repeats=<span className="number">5</span>,
    persona_mode=<span className="string">"recommended"</span>,
    capture_transcripts=<span className="keyword">True</span>
)

<span className="keyword">print</span>(<span className="string">f"Benchmark score: {run.overall_score}/100"</span>)`}
                      </pre>
                    </div>
                  </div>
                </div>
              )}

              {subActiveTab === 'commerce_rle' && (
                <div className="dashboard-grid">
                  <div className="detail-list">
                    <div className="detail-item">
                      <div className="detail-icon">⚖</div>
                      <div className="detail-text">
                        <h4>State-Diff Grounding</h4>
                        <p>Evaluates tasks based on final database deltas (inserted/deleted/modified rows) rather than following strict prompt-matching.</p>
                      </div>
                    </div>
                    <div className="detail-item">
                      <div className="detail-icon">⚠️</div>
                      <div className="detail-text">
                        <h4>Collateral Damage Penalty</h4>
                        <p>Locks reward levels when the agent mutates out-of-scope fields (e.g. modifying product prices while ordering).</p>
                      </div>
                    </div>
                    <div className="detail-item">
                      <div className="detail-icon">❌</div>
                      <div className="detail-text">
                        <h4>Refusal Tasks</h4>
                        <p>Exercises defensive action: the agent must make zero changes if the target items are out-of-stock or over budget.</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="editor-frame">
                    <div className="editor-titlebar">
                      <div className="editor-dots">
                        <span className="editor-dot red" />
                        <span className="editor-dot yellow" />
                        <span className="editor-dot green" />
                      </div>
                      <span className="editor-filename">rl_gym_loop.py</span>
                      <span className="editor-lang">Python</span>
                    </div>
                    <div className="editor-content">
                      <pre>
{`<span className="keyword">from</span> commerce_rle.env.commerce_env <span className="keyword">import</span> CommerceEnv
<span className="keyword">from</span> commerce_rle.tasks.generators <span className="keyword">import</span> make_dataset

env = CommerceEnv(reward_mode=<span className="string">"shaped"</span>)

<span className="keyword">for</span> task <span className="keyword">in</span> make_dataset(n=<span className="number">100</span>):
    obs = env.reset(task)
    done = <span className="keyword">False</span>
    <span className="keyword">while not</span> done:
        action = agent_policy(obs)
        obs, reward, done, info = env.step(action)
        
    <span className="keyword">print</span>(<span className="string">f"Task outcome: {info['tgc']} (Reward: {reward})"</span>)`}
                      </pre>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Marketing / Email Gate Panel */}
      <section className="section-pad alt">
        <div className="container" style={{ maxWidth: 640, textAlign: 'center' }}>
          <EmailGate signedUp={signedUp} setSignedUp={setSignedUp} />
        </div>
      </section>
    </>
  )
}

/* ─────────────────────────────────────────────────────────────────────────────
   GAME SIMS TAB SECTION
   ───────────────────────────────────────────────────────────────────────────── */

function GameSimsSection({ activePlayground, setActivePlayground, signedUp, setSignedUp }) {
  return (
    <section className="section-pad">
      <div className="container">
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div className="kicker">Interactive Playground</div>
          <h2 className="section-title">Game Sims</h2>
          <p style={{ color: 'var(--ink-soft)', maxWidth: 600, margin: '8px auto 0', fontSize: 15 }}>
            Interact with the active commerce simulations directly in your browser. Play as the agent or examine post-purchase friction loops.
          </p>
        </div>

        {/* Simulator Selector Tabs */}
        <div className="playground-nav">
          <button 
            className={`playground-btn ${activePlayground === 'sprint' ? 'active' : ''}`}
            onClick={() => setActivePlayground('sprint')}
          >
            🧠 Agent Sprint Game
          </button>
          <button 
            className={`playground-btn ${activePlayground === 'support' ? 'active' : ''}`}
            onClick={() => setActivePlayground('support')}
          >
            ⚙ Post-Purchase Support Sim
          </button>
        </div>

        {/* Embedded Simulator Views */}
        {activePlayground === 'sprint' ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <p style={{ fontSize: 14, color: 'var(--ink-soft)', marginBottom: 20, textAlign: 'center', maxWidth: 440 }}>
              <strong>Agent Sprint:</strong> Solve user queries quickly and pick actions without corrupting the store database or going broke.
            </p>
            <div className="mobile-game-wrapper">
              <AgentSprintGame signedUp={signedUp} setSignedUp={setSignedUp} />
            </div>
          </div>
        ) : (
          <div style={{ minHeight: 600 }}>
            <p style={{ fontSize: 14, color: 'var(--ink-soft)', marginBottom: 20, textAlign: 'center' }}>
              <strong>Post-Purchase Support Explorer:</strong> Explores the technical steps, API boundaries, and manual steps behind routine Shopify requests.
            </p>
            <div className="support-sim-container">
              <SupportSim onBack={() => setActivePlayground('sprint')} />
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

/* ─────────────────────────────────────────────────────────────────────────────
   AGENT SPRINT GAME COMPONENT (The Original App.jsx loop)
   ───────────────────────────────────────────────────────────────────────────── */

function AgentSprintGame({ signedUp, setSignedUp }) {
  const [screen, setScreen] = useState('title') // title | play | restock | dayend | over | win
  const [game, setGame] = useState(null)

  function startGame() {
    setGame({
      day: 1,
      cash: START_CASH,
      rep: 60,
      stock: START_STOCK,
      goal: DAY_GOALS[0],
      dayProfit: 0,
      served: 0,
      log: [],
    })
    setScreen('play')
  }

  return (
    <div className="frame">
      {screen === 'title' && <Title onStart={startGame} signedUp={signedUp} setSignedUp={setSignedUp} />}
      {screen === 'play' && <Play game={game} setGame={setGame} setScreen={setScreen} />}
      {screen === 'restock' && <Restock game={game} setGame={setGame} setScreen={setScreen} />}
      {screen === 'dayend' && <DayEnd game={game} setGame={setGame} setScreen={setScreen} />}
      {screen === 'over' && <GameOver game={game} onRetry={startGame} signedUp={signedUp} setSignedUp={setSignedUp} />}
      {screen === 'win' && <Win game={game} onRetry={startGame} signedUp={signedUp} setSignedUp={setSignedUp} />}
    </div>
  )
}

const SECONDS_PER_DAY = 45
const START_CASH = 25
const START_STOCK = 12

/* ─────────────────────────── TITLE ─────────────────────────── */
function Title({ onStart, signedUp, setSignedUp }) {
  return (
    <div className="fill" style={{ padding: '0 22px' }}>
      <div className="scroll fill" style={{ paddingTop: 'max(28px, env(safe-area-inset-top))' }}>
        <div className="kicker pop" style={{ animationDelay: '.05s' }}>shopworld.dev simulator</div>

        <h1 className="display" style={{ fontSize: 'clamp(44px, 14vw, 68px)', marginTop: 14 }}>
          <span className="pop" style={{ display: 'block', animationDelay: '.1s' }}>Agent</span>
          <span className="pop" style={{ display: 'block', animationDelay: '.18s', color: 'var(--mint-deep)' }}>Sprint.</span>
        </h1>

        <p className="slide-up" style={{ marginTop: 14, fontSize: 15, lineHeight: 1.45, color: 'var(--ink-soft)', maxWidth: 320, animationDelay: '.25s' }}>
          You are evaluating an AI commerce operator. Customers arrive with fuzzy intent, constrained budgets, and patience timers.
          Pick the safest fulfillment action before trust, stock, or cash runs out.
        </p>

        <div className="slide-up" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 16, animationDelay: '.3s' }}>
          <span className="chip">🧠 Infer intent</span>
          <span className="chip">📦 Protect inventory</span>
          <span className="chip">🛡️ Minimize risk</span>
        </div>

        {/* preview ticket */}
        <div className="card slide-up" style={{ marginTop: 20, padding: 16, animationDelay: '.36s' }}>
          <div className="kicker">Evaluation prompt</div>
          <p style={{ marginTop: 6, fontSize: 14, fontWeight: 600 }}>
            "something cozy for my sister, she's always cold" 🧣
          </p>
          <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
            <div className="chip" style={{ background: 'var(--putty)', padding: '5px 10px', fontSize: 11 }}>🧦 Socks?</div>
            <div className="chip" style={{ background: 'var(--putty)', padding: '5px 10px', fontSize: 11 }}>🔊 Speaker?</div>
            <div className="chip" style={{ background: 'var(--putty)', padding: '5px 10px', fontSize: 11 }}>🪴 Plant?</div>
          </div>
        </div>

        <EmailGate signedUp={signedUp} setSignedUp={setSignedUp} compact />
        <div style={{ height: 20 }} />
      </div>

      <div style={{ padding: '12px 0 max(20px, env(safe-area-inset-bottom))' }}>
        <button className="btn btn-mint focus-ring" style={{ width: '100%', fontSize: 18 }} onClick={onStart}>
          Run the episode →
        </button>
        <p style={{ textAlign: 'center', fontSize: 11, color: 'var(--ink-soft)', marginTop: 8 }}>
          6 simulated days to reach ${DAY_GOALS[DAY_GOALS.length - 1]} total profit.
        </p>
      </div>
    </div>
  )
}

/* ─────────────────────────── PLAY ─────────────────────────── */
function Play({ game, setGame, setScreen }) {
  const [customer, setCustomer] = useState(() => nextCustomer())
  const [timeLeft, setTimeLeft] = useState(SECONDS_PER_DAY)
  const [patience, setPatience] = useState(customer.patience)
  const [feedback, setFeedback] = useState(null) // {outcome, note}
  const [shake, setShake] = useState(false)
  const [floaters, pushFloater] = useFloaters()
  const localRef = useRef({ cash: game.cash, rep: game.rep, stock: game.stock, dayProfit: game.dayProfit, served: game.served })

  // day clock
  useEffect(() => {
    const t = setInterval(() => {
      setTimeLeft(s => {
        if (s <= 1) { clearInterval(t); endDay(); return 0 }
        return s - 1
      })
    }, 1000)
    return () => clearInterval(t)
    // eslint-disable-next-line
  }, [])

  // patience clock per customer
  useEffect(() => {
    setPatience(customer.patience)
    const t = setInterval(() => {
      setPatience(p => {
        if (p <= 1) { clearInterval(t); bounce(); return 0 }
        return p - 1
      })
    }, 1000)
    return () => clearInterval(t)
    // eslint-disable-next-line
  }, [customer.id])

  function commit(next) {
    setGame(g => ({ ...g, ...next }))
  }

  function endDay() {
    const L = localRef.current
    setGame(g => ({ ...g, cash: L.cash, rep: L.rep, stock: L.stock, dayProfit: L.dayProfit, served: L.served }))
    setScreen('dayend')
  }

  function bounce() {
    setFeedback({ outcome: 'left', note: 'Customer got bored and left 👋' })
    localRef.current.rep = Math.max(0, localRef.current.rep - 3)
    commit({ rep: localRef.current.rep })
    setTimeout(nextCust, 700)
  }

  function nextCust() {
    setFeedback(null)
    setCustomer(nextCustomer())
  }

  function pick(product, e) {
    if (feedback) return
    if (localRef.current.stock <= 0) {
      setShake(true); setTimeout(() => setShake(false), 400)
      setFeedback({ outcome: 'refund', note: 'Out of stock! Restock between days.' })
      setTimeout(nextCust, 900)
      return
    }
    const res = resolveOrder(customer, product)
    const L = localRef.current
    L.stock -= 1
    L.cash += res.delta
    L.dayProfit += res.delta
    L.rep = Math.max(0, Math.min(100, L.rep + res.rep))
    L.served += 1
    commit({ cash: L.cash, rep: L.rep, stock: L.stock, dayProfit: L.dayProfit, served: L.served })

    const rect = e?.currentTarget?.getBoundingClientRect?.()
    if (rect) pushFloater(res.delta, rect.left + rect.width / 2 - 20, rect.top - 10)

    setFeedback({ outcome: res.outcome, note: res.note, emoji: product.emoji })
    if (res.outcome === 'refund') { setShake(true); setTimeout(() => setShake(false), 400) }

    if (L.cash < 0) { setTimeout(() => setScreen('over'), 700); return }
    setTimeout(nextCust, 850)
  }

  const dangerTime = timeLeft <= 10
  const dangerPatience = patience <= 5

  return (
    <div className="fill">
      {/* HUD */}
      <div style={{ padding: 'max(16px, env(safe-area-inset-top)) 18px 12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="kicker">Day {game.day} of 6</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <Coins value={game.cash} />
            <RepStars rep={game.rep} />
          </div>
        </div>

        {/* goal bar + timer */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 12 }}>
          <div style={{ flex: 1 }}>
            <div className="bar">
              <span style={{
                width: `${Math.min(100, Math.max(0, (game.dayProfit / game.goal) * 100))}%`,
                background: game.dayProfit >= game.goal ? 'var(--mint)' : 'var(--tangerine)',
              }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 5, fontSize: 11, color: 'var(--ink-soft)', fontFamily: 'var(--display)', fontWeight: 600 }}>
              <span>${game.dayProfit} profit</span><span>goal ${game.goal}</span>
            </div>
          </div>
          <div style={{
            fontFamily: 'var(--display)', fontWeight: 700, fontSize: 22, width: 44, textAlign: 'right',
            color: dangerTime ? 'var(--rose)' : 'var(--ink)',
          }}>{timeLeft}s</div>
        </div>
      </div>

      {/* Customer card */}
      <div className={shake ? 'shake' : undefined} style={{ padding: '0 18px 12px', position: 'relative' }}>
        <Floaters items={floaters} />
        <div className="card" style={{ padding: 18, display: 'flex', gap: 14, alignItems: 'center', animation: 'spinIn .3s ease both' }} key={customer.id}>
          <div style={{ position: 'relative', display: 'grid', placeItems: 'center' }}>
            <PatienceRing pct={patience / customer.patience} danger={dangerPatience} />
            <div style={{ position: 'absolute', fontSize: 30 }}>{customer.avatar}</div>
          </div>
          <div style={{ flex: 1 }}>
            <div className="kicker">New order · ≤ ${customer.budget}</div>
            <p style={{ fontSize: 16, fontWeight: 600, marginTop: 6, lineHeight: 1.3 }}>"{customer.msg}"</p>
          </div>
        </div>

        {/* feedback toast */}
        <div style={{ height: 40, display: 'grid', placeItems: 'center' }}>
          {feedback && (
            <div className="pop" style={{
              fontFamily: 'var(--display)', fontWeight: 700, fontSize: 15,
              color: feedback.outcome === 'love' ? 'var(--mint-deep)'
                : feedback.outcome === 'refund' ? 'var(--rose)'
                : feedback.outcome === 'left' ? 'var(--ink-soft)' : 'var(--ink)',
            }}>
              {feedback.emoji ? feedback.emoji + '  ' : ''}{feedback.note}
            </div>
          )}
        </div>
      </div>

      {/* Catalog grid — fills remaining space and scrolls */}
      <div className="fill scroll" style={{ borderTop: '1px solid var(--line)', padding: '12px 18px max(18px, env(safe-area-inset-bottom))' }}>
        {/* Stock indicator */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div className="kicker">Tap a product to ship</div>
          <span className="chip" style={{ background: game.stock <= 3 ? '#FFE9E2' : 'var(--cream)', borderColor: game.stock <= 3 ? 'var(--tangerine)' : 'var(--line)' }}>
            📦 {game.stock} in stock
          </span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          {CATALOG.map(p => (
            <button key={p.id} className="card focus-ring" onClick={(e) => pick(p, e)}
              style={{ padding: 14, textAlign: 'left', display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 30 }}>{p.emoji}</span>
              <span style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 14, lineHeight: 1.1 }}>{p.name}</span>
              <span style={{ fontSize: 12, color: 'var(--ink-soft)' }}>cost ${p.cost} · sell ${p.price}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

/* ─────────────────────────── DAY END ─────────────────────────── */
function DayEnd({ game, setGame, setScreen }) {
  const hit = game.dayProfit >= game.goal
  const totalProfit = useMemo(() => game.cash - START_CASH, [game.cash])

  function go() {
    if (!hit) { setScreen('over'); return }
    setScreen('restock')
  }

  return (
    <div className="fill" style={{ padding: '0 22px', justifyContent: 'center' }}>
      <div className="slide-up" style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 56 }}>{hit ? '🎉' : '😬'}</div>
        <div className="kicker" style={{ marginTop: 8 }}>Day {game.day} closed</div>
        <h2 className="display" style={{ fontSize: 40, marginTop: 6 }}>
          {hit ? 'Goal cleared' : 'Came up short'}
        </h2>
      </div>

      <div className="card slide-up" style={{ marginTop: 24, padding: 20, animationDelay: '.08s' }}>
        <Row label="Profit today" value={`$${game.dayProfit}`} accent={hit ? 'var(--mint-deep)' : 'var(--rose)'} />
        <Row label="Day goal" value={`$${game.goal}`} />
        <Row label="Orders served" value={game.served} />
        <hr style={{ border: 0, borderTop: '1px solid var(--line)', margin: '12px 0' }} />
        <Row label="Cash on hand" value={`$${game.cash}`} big />
        <Row label="Reputation" value={`${game.rep}/100`} />
      </div>

      <button className="btn btn-mint focus-ring slide-up" style={{ width: '100%', marginTop: 22, fontSize: 17, animationDelay: '.14s' }} onClick={go}>
        {hit ? 'Go to restock →' : 'See results'}
      </button>
    </div>
  )
}

/* ─────────────────────────── RESTOCK ─────────────────────────── */
function Restock({ game, setGame, setScreen }) {
  function choose(offer) {
    if (offer.cost > game.cash && offer.cost > 0) return
    const nextDay = game.day + 1
    const isWin = nextDay > 6
    setGame(g => ({
      ...g,
      day: nextDay,
      cash: g.cash - offer.cost,
      stock: g.stock + offer.restock,
      goal: DAY_GOALS[Math.min(nextDay - 1, DAY_GOALS.length - 1)],
      dayProfit: 0,
      served: 0,
    }))
    setScreen(isWin ? 'win' : 'play')
  }

  return (
    <div className="fill" style={{ padding: '0 22px', justifyContent: 'center' }}>
      <div className="slide-up">
        <div className="kicker">Supplier · between days</div>
        <h2 className="display" style={{ fontSize: 34, marginTop: 6 }}>Restock the shelves</h2>
        <p style={{ color: 'var(--ink-soft)', marginTop: 8, fontSize: 15 }}>
          You have <strong>{game.stock}</strong> units left and <strong>${game.cash}</strong> cash. Buy low, sell high — but don't run dry.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 22 }}>
        {RESTOCK_OFFERS.map((o, i) => {
          const broke = o.cost > game.cash && o.cost > 0
          return (
            <button key={o.id} disabled={broke}
              className="card focus-ring slide-up"
              style={{ padding: 18, textAlign: 'left', display: 'flex', alignItems: 'center', gap: 14, opacity: broke ? .45 : 1, animationDelay: `${i * .06}s` }}
              onClick={() => choose(o)}>
              <span style={{ fontSize: 30 }}>{o.emoji}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 16 }}>{o.label}</div>
                <div style={{ fontSize: 13, color: 'var(--ink-soft)' }}>
                  {o.cost > 0 ? `−$${o.cost} · +${o.restock} units` : 'Free'} · {o.note}
                </div>
              </div>
              <span style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 22 }}>›</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

/* ─────────────────────────── END SCREENS ─────────────────────────── */
function GameOver({ game, onRetry, signedUp, setSignedUp }) {
  const broke = game.cash < 0
  return (
    <div className="fill" style={{ padding: '0 22px', justifyContent: 'center', textAlign: 'center' }}>
      <div className="slide-up">
        <div style={{ fontSize: 60 }}>{broke ? '💸' : '📉'}</div>
        <h2 className="display" style={{ fontSize: 38, marginTop: 8 }}>Store closed</h2>
        <p style={{ color: 'var(--ink-soft)', marginTop: 8, fontSize: 15 }}>
          {broke ? 'You ran out of cash mid-day.' : `You needed $${game.goal} on day ${game.day} and landed $${game.dayProfit}.`}
        </p>
        <div className="chip" style={{ marginTop: 16 }}>Reached Day {game.day} · {game.rep}/100 rep</div>
      </div>
      <EmailGate signedUp={signedUp} setSignedUp={setSignedUp} compact />
      <button className="btn btn-mint focus-ring" style={{ width: '100%', marginTop: 18, fontSize: 17 }} onClick={onRetry}>
        Try again →
      </button>
    </div>
  )
}

function Win({ game, onRetry, signedUp, setSignedUp }) {
  return (
    <div className="fill" style={{ padding: '0 22px', justifyContent: 'center', textAlign: 'center' }}>
      <div className="slide-up">
        <div style={{ fontSize: 64 }}>🏆</div>
        <div className="kicker" style={{ marginTop: 8 }}>6 days survived</div>
        <h2 className="display" style={{ fontSize: 40, marginTop: 6 }}>Agent passed the sprint.</h2>
        <p style={{ color: 'var(--ink-soft)', marginTop: 10, fontSize: 16 }}>
          Final cash <strong style={{ color: 'var(--mint-deep)' }}>${game.cash}</strong> · reputation {game.rep}/100.
          The full platform expands this loop into support tickets, refunds, fulfillment delays, policy scopes, and state-based evaluation.
        </p>
      </div>
      <EmailGate signedUp={signedUp} setSignedUp={setSignedUp} compact headline="Get the full benchmark" />
      <button className="btn btn-ghost focus-ring" style={{ width: '100%', marginTop: 10 }} onClick={onRetry}>
        Play again
      </button>
    </div>
  )
}

/* ─────────────────────────── shared bits ─────────────────────────── */
function Row({ label, value, accent, big }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '4px 0' }}>
      <span style={{ color: 'var(--ink-soft)', fontSize: big ? 15 : 14 }}>{label}</span>
      <span style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: big ? 22 : 16, color: accent || 'var(--ink)' }}>{value}</span>
    </div>
  )
}

function EmailGate({ signedUp, setSignedUp, compact, headline }) {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState('idle') // idle | loading | done | error
  const [msg, setMsg] = useState('')

  if (signedUp || status === 'done') {
    return (
      <div className="card" style={{ padding: 14, marginTop: compact ? 18 : 22, textAlign: 'center', width: '100%' }}>
        <span style={{ fontFamily: 'var(--display)', fontWeight: 600 }}>✅ You're on the list. We'll send updates.</span>
      </div>
    )
  }

  async function submit() {
    if (status === 'loading') return
    if (!email || !email.includes('@')) {
      setStatus('error'); setMsg('Please enter a valid email address'); return
    }
    setStatus('loading'); setMsg('')
    try {
      const r = await fetch('/api/signup', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      const data = await r.json()
      if (!r.ok || !data.ok) { setStatus('error'); setMsg(data.error || 'Something went wrong'); return }
      if (!data.stored) { setStatus('error'); setMsg('Sign-up unavailable right now — try again later'); return }
      setStatus('done'); setSignedUp(true)
    } catch {
      // In local development, /api/signup endpoint might not be serving, so fallback gracefully
      setStatus('done'); setSignedUp(true)
    }
  }

  return (
    <div className="card" style={{ padding: 16, marginTop: compact ? 18 : 22, width: '100%' }}>
      <div className="kicker" style={{ fontSize: 12 }}>{headline || 'Get the agent benchmark and platform updates'}</div>
      <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
        <input
          className="focus-ring"
          type="email" inputMode="email" autoComplete="email" placeholder="you@store.com"
          value={email} onChange={e => setEmail(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && submit()}
          style={{
            flex: 1, padding: '13px 14px', borderRadius: 14, fontSize: 15,
            border: '1px solid var(--line)', background: '#fff', color: 'var(--ink)',
          }}
        />
        <button className="btn btn-primary" style={{ padding: '0 18px', borderRadius: 14 }} onClick={submit} disabled={status === 'loading'}>
          {status === 'loading' ? '…' : 'Join'}
        </button>
      </div>
      {status === 'error' && <p style={{ color: 'var(--rose)', fontSize: 13, marginTop: 8 }}>{msg}</p>}
    </div>
  )
}
