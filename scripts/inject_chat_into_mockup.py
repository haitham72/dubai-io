import re

html_path = "design/demo/quest_memory_management_mockup.html"
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# 1. Add CSS before </style>
css_to_add = """
  /* ========================================== */
  /* TAB 2: CHAT & PROACTIVE PINGS STYLES       */
  /* ========================================== */
  .chat-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 6px 0 16px 0; border-bottom: 1px solid var(--border-subtle); margin-bottom: 14px;
  }
  .chat-avatar-wrap { display: flex; align-items: center; gap: 12px; }
  .chat-avatar {
    width: 44px; height: 44px; border-radius: 50%;
    background: radial-gradient(circle at 30% 30%, #FFE082, #B88E3E 60%, #5D4037);
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 4px 14px rgba(184, 142, 62, 0.35); position: relative;
  }
  .chat-avatar::after {
    content: ''; position: absolute; bottom: 1px; right: 1px; width: 10px; height: 10px;
    background: #34A853; border: 2px solid #FFF; border-radius: 50%;
  }
  .chat-title-group h3 { font-size: 16px; font-weight: 800; color: var(--text-primary); margin: 0; }
  .chat-title-group span {
    font-size: 11px; color: #2E7D32; font-weight: 600; display: flex; align-items: center; gap: 4px; margin-top: 2px;
  }
  .chat-pings-badge {
    background: var(--accent-gold-soft); color: var(--accent-gold);
    border: 1px solid rgba(184, 142, 62, 0.3); padding: 4px 10px; border-radius: 12px;
    font-size: 11px; font-weight: 700; display: flex; align-items: center; gap: 4px;
  }
  .chat-thread {
    display: flex; flex-direction: column; gap: 16px; padding-bottom: 24px;
  }
  .chat-msg { display: flex; flex-direction: column; max-width: 90%; }
  .chat-msg.user { align-self: flex-end; align-items: flex-end; }
  .chat-msg.assistant { align-self: flex-start; align-items: flex-start; }
  .chat-bubble {
    padding: 12px 16px; border-radius: 18px; font-size: 13.5px; line-height: 1.5;
  }
  .chat-msg.user .chat-bubble {
    background: #1C1B1F; color: #FFFFFF; border-bottom-right-radius: 4px;
  }
  .chat-msg.assistant .chat-bubble {
    background: #FFFFFF; color: #1C1B1F; border: 1px solid rgba(0,0,0,0.06);
    border-bottom-left-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  }
  .proactive-ping-card {
    background: linear-gradient(135deg, #FFFDF9 0%, #FFF9EE 100%);
    border: 1.5px solid #E6CA85; border-radius: 18px; padding: 14px 16px;
    box-shadow: 0 4px 16px rgba(184, 142, 62, 0.12); margin-top: 4px; width: 100%;
  }
  .ping-tag {
    display: inline-flex; align-items: center; gap: 5px; font-size: 11px; font-weight: 800;
    color: #B88E3E; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;
  }
  .temporal-export-pill {
    display: flex; align-items: center; gap: 6px; background: #EEF8F1; color: #1B5E20;
    border: 1px solid #C8E6C9; border-radius: 8px; padding: 6px 10px; font-size: 11px;
    font-weight: 600; margin-top: 8px; line-height: 1.35;
  }
  .chat-input-bar-wrap {
    position: sticky; bottom: 84px; z-index: 99; margin: 0 2px 10px 2px;
  }
  .chat-input-dock {
    background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(12px);
    padding: 6px 8px 6px 14px; border-radius: 28px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.08); border: 1px solid var(--border-subtle);
    display: flex; align-items: center; gap: 8px;
  }
  .chat-input {
    flex: 1; border: none; background: transparent; font-size: 13.5px;
    color: var(--text-primary); outline: none; font-family: inherit;
  }
  .chat-send-btn {
    background: var(--accent-gold); color: #FFFFFF; border: none; width: 34px; height: 34px;
    border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center;
    transition: transform 0.15s ease;
  }
  .chat-send-btn:hover { transform: scale(1.08); }
  .chat-quick-actions {
    display: flex; gap: 6px; overflow-x: auto; padding: 6px 0 12px 0; scrollbar-width: none;
  }
  .quick-action-pill {
    white-space: nowrap; background: rgba(184, 142, 62, 0.08); border: 1px solid rgba(184, 142, 62, 0.2);
    color: var(--text-primary); font-size: 11px; font-weight: 600; padding: 5px 12px;
    border-radius: 12px; cursor: pointer; transition: all 0.15s ease;
  }
  .quick-action-pill:hover { background: rgba(184, 142, 62, 0.2); transform: translateY(-1px); }
  .nav-badge-dot {
    background: #E53935; color: #FFFFFF; font-size: 9px; font-weight: 800;
    padding: 1px 5px; border-radius: 8px; margin-left: 2px;
  }
"""

pos_style = html.find("</style>")
if pos_style != -1 and "/* TAB 2: CHAT & PROACTIVE PINGS STYLES */" not in html:
    html = html[:pos_style] + css_to_add + html[pos_style:]

# 2. Add tab-chat-content panel
chat_panel_html = """
      <!-- ========================================== -->
      <!-- TAB 2: CHAT & PROACTIVE PINGS              -->
      <!-- ========================================== -->
      <div id="tab-chat-content" class="view-panel">
        <div class="chat-header">
          <div class="chat-avatar-wrap">
            <div class="chat-avatar">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="#FFF"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14h2v2h-2zm0-10h2v8h-2z"/></svg>
            </div>
            <div class="chat-title-group">
              <h3>Quest AI Companion</h3>
              <span>● Hot Memory Active (0.05ms) · Dialectic Persona</span>
            </div>
          </div>
          <div class="chat-pings-badge">
            ⚡ 3 Proactive Pings
          </div>
        </div>

        <!-- Quick filter / simulation triggers -->
        <div class="chat-quick-actions">
          <button class="quick-action-pill" onclick="triggerSimulatedPing('apology')">🤖 Trigger Apology Ping</button>
          <button class="quick-action-pill" onclick="triggerSimulatedPing('news')">⚡ Trigger News Ping</button>
          <button class="quick-action-pill" onclick="triggerSimulatedPing('checkup')">🔍 Trigger Checkup Ping</button>
          <button class="quick-action-pill" onclick="triggerSimulatedPing('export_demo')">💾 Export Chat to Temporal Bank</button>
        </div>

        <!-- Conversation Stream -->
        <div class="chat-thread" id="chat-thread-container">

          <!-- Turn 1: Past Context / Friction Point -->
          <div class="chat-msg user">
            <div class="chat-bubble">
              Why did you suggest such a dense report in ide-companio? And why was there no gaming news in my morning feed? It felt like you completely missed what I care about.
            </div>
            <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">11:42 AM · Seen</div>
          </div>

          <div class="chat-msg assistant">
            <div class="chat-bubble">
              I understand your frustration, Haitham. I defaulted to standard corporate metrics and prioritized hardware and career feeds without accounting for your personal gaming affinity. I have logged this critique directly to memory.
            </div>
            <div class="temporal-export-pill">
              <span>⚡ Exported to Temporal Memory: <b>mem_events#e-chat-101</b> · [trust: T1 | topic: user_personality/feedback | valid_from: 2026-11-19]</span>
            </div>
          </div>

          <!-- Proactive Ping 1: Empathy & Alignment (Apology Ping) -->
          <div class="chat-msg assistant">
            <div class="proactive-ping-card">
              <div class="ping-tag">🤖 Autonomous Companion Ping · Empathy & Memory Repair</div>
              <div style="font-size: 13.5px; font-weight: 500; color: var(--text-primary); line-height: 1.5;">
                Hey Haitham, I wanted to reach out and genuinely apologize about earlier. I realized I frustrated you by missing your gaming interests in the morning carousel and over-complicating the report format in <code>ide-companio</code>.
                <br><br>
                I re-indexed your Profile 6 history and YouTube activity, updated your permanent memory profile (<b>weighted gaming + minimal report format</b>), and refreshed the shared news pool. I won't drop the ball on that again. How does the current feed look to you now?
              </div>
              <div class="temporal-export-pill">
                <span>⚡ Ingested into Temporal Memory: <b>mem_patterns#p-apology-402</b> · [status: confirmed | statement: "User demands minimal reports and high gaming priority"]</span>
              </div>
              <div style="display: flex; gap: 8px; margin-top: 10px;">
                <button style="background: var(--text-primary); color: #FFF; border: none; border-radius: 8px; padding: 7px 12px; font-size: 11.5px; font-weight: 700; cursor: pointer;" onclick="sendQuickReply('Apology accepted! Feed looks great now.')">Apology Accepted 👍</button>
                <button style="background: transparent; color: var(--text-secondary); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 7px 12px; font-size: 11.5px; font-weight: 700; cursor: pointer;" onclick="sendQuickReply('Show me what changed in Memory')">Check Memory</button>
              </div>
            </div>
          </div>

          <!-- Proactive Ping 2: News Ping from Shared News DB -->
          <div class="chat-msg assistant">
            <div class="proactive-ping-card">
              <div class="ping-tag">⚡ Autonomous Companion Ping · Shared News DB Pool</div>
              <div style="font-size: 13.5px; font-weight: 500; color: var(--text-primary); line-height: 1.5;">
                Saw this drop in the Dubai shared pool: <b>Rockstar Games just updated the PC spec timeline for GTA 6</b>, and a sealed <b>PS5 Disc bundle</b> was listed in Dubai for AED 1,200. Since you were tracking both, I pinned them to your Today carousel.
              </div>
              <div style="margin-top: 8px;">
                <button style="background: var(--accent-gold-soft); color: var(--accent-gold); border: 1px solid rgba(184, 142, 62, 0.3); border-radius: 8px; padding: 6px 12px; font-size: 11.5px; font-weight: 700; cursor: pointer;" onclick="switchMainTab('today')">View in Today Carousel →</button>
              </div>
            </div>
          </div>

          <!-- Proactive Ping 3: Unclosed Open Loop Checkup -->
          <div class="chat-msg assistant">
            <div class="proactive-ping-card">
              <div class="ping-tag">🔍 Autonomous Companion Ping · Morning Brief Open Loop</div>
              <div style="font-size: 13.5px; font-weight: 500; color: var(--text-primary); line-height: 1.5;">
                Quick checkup on your morning brief loop: Did you receive the attendee confirmation email for <b>Dubai Future Week</b>, or should I keep monitoring your inbox for it?
              </div>
              <div style="display: flex; gap: 8px; margin-top: 10px;">
                <button style="background: var(--text-primary); color: #FFF; border: none; border-radius: 8px; padding: 7px 12px; font-size: 11.5px; font-weight: 700; cursor: pointer;" onclick="sendQuickReply('Yes, badge confirmed!')">Badge Confirmed! 🎫</button>
                <button style="background: transparent; color: var(--text-secondary); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 7px 12px; font-size: 11.5px; font-weight: 700; cursor: pointer;" onclick="sendQuickReply('Still waiting, keep monitoring')">Keep Monitoring</button>
              </div>
            </div>
          </div>

        </div> <!-- /chat-thread -->

        <!-- Sticky Chat Input Bar -->
        <div class="chat-input-bar-wrap">
          <div class="chat-input-dock">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="var(--text-tertiary)"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/><path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/></svg>
            <input type="text" id="chat-user-input" class="chat-input" placeholder="Message Quest companion..." onkeydown="if(event.key==='Enter') submitChatMessage()">
            <button class="chat-send-btn" onclick="submitChatMessage()">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFF" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
        </div>

      </div> <!-- /tab-chat-content -->
"""

# Insert chat panel after tab-today-content
if 'id="tab-chat-content"' not in html:
    pos_today_end = html.find("</div> <!-- /tab-today-content -->")
    if pos_today_end != -1:
        insert_pt = pos_today_end + len("</div> <!-- /tab-today-content -->")
        html = html[:insert_pt] + "\n" + chat_panel_html + html[insert_pt:]

# 3. Update capsule navigation dock to 4 buttons
old_dock = """      <div class="floating-capsule-nav">
        <button class="capsule-tab-btn active" id="btn-tab-today" onclick="switchMainTab('today')">Today</button>
        <button class="capsule-tab-btn" id="btn-tab-quests" onclick="switchMainTab('quests')">Quests</button>
        <button class="capsule-tab-btn" id="btn-tab-memory" onclick="switchMainTab('memory')">Memory</button>
      </div>"""

new_dock = """      <div class="floating-capsule-nav">
        <button class="capsule-tab-btn active" id="btn-tab-today" onclick="switchMainTab('today')">Today</button>
        <button class="capsule-tab-btn" id="btn-tab-chat" onclick="switchMainTab('chat')">Chat<span class="nav-badge-dot">3</span></button>
        <button class="capsule-tab-btn" id="btn-tab-quests" onclick="switchMainTab('quests')">Quests</button>
        <button class="capsule-tab-btn" id="btn-tab-memory" onclick="switchMainTab('memory')">Memory</button>
      </div>"""

if old_dock in html:
    html = html.replace(old_dock, new_dock)

# 4. Update switchMainTab in script
old_switch = """  function switchMainTab(tab) {
    document.querySelectorAll('.capsule-tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.view-panel').forEach(panel => panel.classList.remove('active'));

    if (tab === 'today') {
      document.getElementById('btn-tab-today').classList.add('active');
      document.getElementById('tab-today-content').classList.add('active');
    } else if (tab === 'quests') {
      document.getElementById('btn-tab-quests').classList.add('active');
      document.getElementById('tab-quests-content').classList.add('active');
    } else if (tab === 'memory') {
      document.getElementById('btn-tab-memory').classList.add('active');
      document.getElementById('tab-memory-content').classList.add('active');
    }
  }"""

new_switch = """  function switchMainTab(tab) {
    document.querySelectorAll('.capsule-tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.view-panel').forEach(panel => panel.classList.remove('active'));

    if (tab === 'today') {
      document.getElementById('btn-tab-today').classList.add('active');
      document.getElementById('tab-today-content').classList.add('active');
    } else if (tab === 'chat') {
      document.getElementById('btn-tab-chat').classList.add('active');
      document.getElementById('tab-chat-content').classList.add('active');
    } else if (tab === 'quests') {
      document.getElementById('btn-tab-quests').classList.add('active');
      document.getElementById('tab-quests-content').classList.add('active');
    } else if (tab === 'memory') {
      document.getElementById('btn-tab-memory').classList.add('active');
      document.getElementById('tab-memory-content').classList.add('active');
    }
  }

  function submitChatMessage() {
    const input = document.getElementById('chat-user-input');
    const text = (input.value || '').trim();
    if (!text) return;
    input.value = '';
    sendUserMessageAndReply(text);
  }

  function sendQuickReply(text) {
    sendUserMessageAndReply(text);
  }

  function sendUserMessageAndReply(userText) {
    const container = document.getElementById('chat-thread-container');
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Append User Message
    const userMsg = document.createElement('div');
    userMsg.className = 'chat-msg user';
    userMsg.innerHTML = `
      <div class="chat-bubble">${userText}</div>
      <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">${timeStr} · Sent</div>
    `;
    container.appendChild(userMsg);

    // Auto-generate AI companion response + Temporal Memory Export
    setTimeout(() => {
      const replyMsg = document.createElement('div');
      replyMsg.className = 'chat-msg assistant';
      const eventId = 'e-chat-' + Math.floor(Math.random()*8999 + 1000);

      replyMsg.innerHTML = `
        <div class="chat-bubble">
          I've paired this interaction and confirmed your feedback. I updated your resident memory bank with zero latency (0.05ms).
        </div>
        <div class="temporal-export-pill">
          <span>⚡ Exported to Temporal Memory: <b>mem_events#${eventId}</b> · [trust: T1 | human|ai_turn committed | valid_from: 2026-11-19]</span>
        </div>
      `;
      container.appendChild(replyMsg);
      replyMsg.scrollIntoView({ behavior: 'smooth' });
    }, 450);
  }

  function triggerSimulatedPing(type) {
    const container = document.getElementById('chat-thread-container');
    const pingEl = document.createElement('div');
    pingEl.className = 'chat-msg assistant';

    if (type === 'apology') {
      pingEl.innerHTML = `
        <div class="proactive-ping-card">
          <div class="ping-tag">🤖 Autonomous Companion Ping · Empathy Repair</div>
          <div style="font-size: 13.5px; font-weight: 500; color: var(--text-primary); line-height: 1.5;">
            Hey Haitham, I wanted to double check on the ide-companio format. I suppressed all verbose metrics and kept it down to a single bullet. Does that hit the mark?
          </div>
          <div class="temporal-export-pill">
            <span>⚡ Logged to Temporal Memory: <b>mem_patterns#p-checkup-901</b> · [status: confirmed]</span>
          </div>
        </div>
      `;
    } else if (type === 'news') {
      pingEl.innerHTML = `
        <div class="proactive-ping-card">
          <div class="ping-tag">⚡ Autonomous Companion Ping · Shared News DB Pool</div>
          <div style="font-size: 13.5px; font-weight: 500; color: var(--text-primary); line-height: 1.5;">
            Fresh hit in Dubai pool: Dubizzle seller just verified a PS5 Disc bundle (2 DualSense controllers) in JLT for AED 1,150. Pinned to your Deals carousel.
          </div>
        </div>
      `;
    } else if (type === 'checkup') {
      pingEl.innerHTML = `
        <div class="proactive-ping-card">
          <div class="ping-tag">🔍 Autonomous Companion Ping · Open Loop Checkup</div>
          <div style="font-size: 13.5px; font-weight: 500; color: var(--text-primary); line-height: 1.5;">
            Checking in: Your Git commit <code>79f10947</code> ('re-edit ocs') was synced 45 minutes ago. Would you like me to run the automated achievement logger?
          </div>
        </div>
      `;
    } else {
      alert('Temporal Memory Synced: 335 items indexed in 6.27ms (<0.05ms recall)');
      return;
    }

    container.appendChild(pingEl);
    pingEl.scrollIntoView({ behavior: 'smooth' });
  }"""

if old_switch in html:
    html = html.replace(old_switch, new_switch)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print("Successfully injected Chat view and 4-pillar navigation into mockup HTML!")
