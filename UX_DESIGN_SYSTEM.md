# CosmittoHUB — Enterprise UX/UI Design Proposal
## A Premium Redesign Blueprint by the Product Design Studio

> **Document Type**: UX/UI Enhancement Proposal — Interaction Design Specification  
> **Scope**: Frontend Experience, Workflows, Design System, AI-Native Interactions  
> **Inspiration References**: Linear, Notion, Stripe, Vercel, Framer, Atlassian

---

## Table of Contents

1. [Overall UX Vision & Philosophy](#1-overall-ux-vision--philosophy)
2. [Global UI Redesign](#2-global-ui-redesign)
3. [Ticket Management UX](#3-ticket-management-ux)
4. [Dashboard & Analytics UX](#4-dashboard--analytics-ux)
5. [AI-Powered UX](#5-ai-powered-ux)
6. [Knowledge Base UX](#6-knowledge-base-ux)
7. [Mobile & Responsive UX](#7-mobile--responsive-ux)
8. [Accessibility & Performance UX](#8-accessibility--performance-ux)
9. [Enterprise Productivity Features](#9-enterprise-productivity-features)
10. [Complete Design System](#10-complete-design-system)

---

## 1. Overall UX Vision & Philosophy

### 1.1 The Core UX Thesis

**"CosmittoHUB should feel like the sharpest tool in the room."**

Not the loudest. Not the most colorful. The sharpest — the one that responds before you finish thinking, that surfaces the right information before you know you need it, that disappears into your workflow rather than demanding your attention.

Enterprise software has failed its users for two decades because it confuses *capability* with *complexity*, and *features* with *friction*. Every additional click in a tool used 200 times a day costs 10 seconds × 200 = 33 minutes of productivity lost — per user, per day. With 50 agents, that's 27+ hours of organizational productivity dissolved into bad UX every single day.

CosmittoHUB's UX philosophy is built on a single, non-negotiable principle:

> **Intelligence should reduce work, not add to it. Every interaction must earn its place.**

### 1.2 The Five UX Laws That Govern Every Decision

**Law 1 — The Two-Second Rule**  
Any information a user needs regularly must be reachable in ≤2 seconds from any screen. Not two clicks. Two *seconds* — accounting for human motor time, visual scanning, and decision-making. If a workflow violates this, the layout is wrong.

**Law 2 — Zero Dead Ends**  
Every empty state is an invitation. Every error is a guided recovery. Every action that fails leaves the user better positioned than before it was attempted. There are no cul-de-sacs in this interface — only redirections.

**Law 3 — The 80/20 Surface Law**  
The 20% of actions that compose 80% of daily work are always one keyboard shortcut, one click, or one gesture away. The other 80% of features are present but never in the way. Progressive disclosure is the design mechanism; judgment is the craft.

**Law 4 — Context Travels With the User**  
When a user opens a ticket, every piece of context relevant to that ticket — reporter history, related issues, AI insights, SLA status — is visible *without navigation*. Users should never have to open a second tab to understand the first.

**Law 5 — The Interface Earns Trust Through Speed**  
A slow interface is a dishonest interface — it implies uncertainty. Every interaction responds immediately (even if the server hasn't yet). Optimistic UI is not a technical optimization; it is a trust-building mechanism.

### 1.3 How the Platform Should Feel — The Experiential Brief

**Fast** — Not "fast enough." *Instantly* responsive. When an agent presses J to navigate to the next ticket, it happens in the same 60-100ms a finger tap takes. The sensation must be that of moving through information, not waiting for it.

**Intelligent** — The interface anticipates. When a ticket is opened, the most relevant response draft is already loading. When a filter is applied, the most likely next filter appears as a chip suggestion. When a deadline approaches, the SLA indicator doesn't just change color — it shifts the entire ticket's visual weight in the queue.

**Calm** — No spinning loaders, no aggressive alerts, no modal stacks. Complexity lives below the surface. The idle state of the dashboard conveys operational confidence: smooth, ordered, professional. When something requires attention, it surfaces with precision — not alarm.

**Premium** — Every pixel earns its place. Consistent 8px grid rhythm. Measured use of shadow depth (two levels maximum). Typography that reads at speed. Color used exclusively for meaning, never decoration.

**Frictionless** — Forms auto-focus. Dropdowns accept keyboard input. Bulk selections persist across pagination. The system remembers the last filter applied, the last view used, the last column sorted. Nothing asks for confirmation twice.

**Collaborative** — Presence indicators, live comment typing indicators, @mention systems, and shared views make the tool feel populated — not like a solo productivity tool but like a shared workspace where the team is always visible.

### 1.4 Cognitive Load Reduction Framework

Every screen is evaluated against four cognitive load dimensions:

**Intrinsic load** (complexity of the task itself) — Cannot be eliminated, only scaffolded. Smart defaults, pre-filled fields, and template suggestions reduce the cognitive effort of complex tasks.

**Extraneous load** (complexity added by poor design) — Zero tolerance. Every piece of UI that doesn't serve the current task is removed from the current view. Advanced options live behind progressive disclosure.

**Germane load** (learning and pattern recognition) — Invest here. Consistent component behavior, predictable keyboard shortcuts, spatial memory (things are always where you left them) — these build fluency that compounds over time.

**Emotional load** (anxiety, frustration, uncertainty) — Eliminated through feedback. Every action confirms itself. Every state communicates clearly. The user always knows: what just happened, what is happening now, what will happen next.

### 1.5 Speed & Productivity Philosophy — Specific Targets

| Interaction | Target Duration | Method |
|---|---|---|
| Navigate to any ticket | < 2 seconds | ⌘K command palette + type first 3 chars |
| Open new ticket form | < 0.5 seconds | ⌘N global shortcut |
| Apply a macro | < 1 second | M key + macro number |
| Bulk close 10 tickets | < 8 seconds | Select with J/X, then Shift+R |
| Find any KB article | < 3 seconds | / to open inline search |
| Change ticket status | < 1 second | S key opens status picker |
| Assign ticket | < 2 seconds | A key opens assignee picker |
| Generate AI draft | < 3 seconds | Tab key after opening reply box |

### 1.6 AI-Assisted Workflow Philosophy

AI in CosmittoHUB is *ambient*, not *modal*. It never interrupts. It never demands attention. It offers — and waits.

The interaction model: **AI presents → User decides → User controls**.

Every AI suggestion is:
- **Visually distinct** but not dominant (softer background, AI label)
- **Dismissable** with a single key or click (never sticky)
- **Explainable** — every suggestion has a "Why?" link that expands reasoning
- **Learnable** — accepting/rejecting suggestions trains the model; this is communicated to users as a feature, not a privacy concern

The emotional goal of AI interactions: agents should feel *more capable* after using AI assistance, not *replaced* by it. The language, visual treatment, and interaction model all serve this.

---

## 2. Global UI Redesign

### 2.1 The Shell — Structural Layout Philosophy

The interface is a three-layer shell:

```
┌─────────────────────────────────────────────────────────────────┐
│  CHROME LAYER (always present — 48px top bar)                   │
│  Logo | Workspace Switcher | Global Search | Notifs | Profile   │
├──────────────┬──────────────────────────────────────────────────┤
│              │                                                   │
│  NAVIGATION  │         CONTENT CANVAS                           │
│  LAYER       │         (fills remaining viewport)               │
│  (240px      │                                                   │
│  collapsed:  │                                                   │
│  48px)       │         ┌─────────────────────────────────────┐  │
│              │         │  CONTEXT PANEL (optional, 320px)    │  │
│              │         │  slides in from right               │  │
│              │         └─────────────────────────────────────┘  │
└──────────────┴──────────────────────────────────────────────────┘
```

The content canvas is a 100% viewport-height scrollable area with a stable, non-jumping scrollbar gutter (`scrollbar-gutter: stable`). The navigation never reflows the content — it overlaps at mobile, pushes at desktop.

### 2.2 Top Chrome Bar — 48px Height

**Left zone (240px)**: The Cosmitto wordmark (SVG, 20px tall, red + white) with a workspace switcher chevron to its right. Clicking the chevron opens a full dropdown showing all workspaces the user has access to, their avatar, name, and role within each. The active workspace has a subtle left-border indicator.

**Center zone (flexible)**: Global search bar. Placeholder: "Search tickets, agents, articles... ⌘K". Clicking or pressing ⌘K morphs the bar into the command palette (see §2.5). The search bar has a subtle keyboard shortcut indicator that pulses once on first login to teach the shortcut.

**Right zone (fixed)**: Left to right — AI status indicator (small dot: green = AI active, amber = processing, gray = unavailable) → Notification bell (badge with count, max "99+") → Help icon → Theme toggle (sun/moon, 24px, toggling triggers a smooth 300ms CSS theme transition) → User avatar (32px circle, click = profile dropdown).

**Top bar background**: `rgba(8, 11, 16, 0.92)` in dark mode with `backdrop-filter: blur(12px) saturate(150%)`. This creates the premium frosted glass effect used by Linear, Vercel, and Stripe — the content below is barely visible through the blur, providing depth without opacity.

### 2.3 Navigation Sidebar Redesign

**Expanded state (240px)**:

```
[Cosmitto Logo + Workspace]
━━━━━━━━━━━━━━━━━━━
[search bar: "Filter nav..." ]
━━━━━━━━━━━━━━━━━━━
WORKSPACE
  📊 Dashboard
  🎫 My Tickets          [12]
  👁 All Tickets
  📂 Queue
━━━━━━━━━━━━━━━━━━━
OPERATIONS
  🏢 Departments
  👥 Agents
  📋 Service Catalog
  🔁 Workflows
━━━━━━━━━━━━━━━━━━━
INTELLIGENCE
  📈 Reports
  💡 Knowledge Base
  🤖 AI Insights
━━━━━━━━━━━━━━━━━━━
SETTINGS
  ⚙ Configuration
  🔐 Security
  🔗 Integrations
━━━━━━━━━━━━━━━━━━━
[User avatar | Name | Role]
[⌘ shortcuts] [? help]
```

**Navigation item anatomy** (36px height):
- 16px icon (from Cosmitto icon set, monochrome, 1.5px stroke)
- 8px gap
- 14px/medium text label
- Optional badge (count or status dot) aligned right
- Active state: `background: rgba(220, 38, 38, 0.08)`, left border 2px `#DC2626`, icon + text in `#DC2626`
- Hover state: `background: rgba(255, 255, 255, 0.05)`, 150ms ease transition
- The transition is on `background` and `color` only — not `transform` — to prevent layout jank

**Collapsed state (48px)**: Only icons remain. Badge counts remain visible (positioned top-right of icon). Hovering a nav item in collapsed state shows a tooltip (not a full flyout — a simple label) 8px to the right, with 200ms delay to avoid accidental triggers.

**Collapsing behavior**: The sidebar collapses smoothly over 200ms using `width` transition (not `transform: translateX` which can cause compositing issues). The content canvas adjusts simultaneously (CSS Grid `grid-template-columns` transition). A thin `1px` border on the right side of the sidebar always remains visible at all widths — the visual anchor.

**Pinned items**: Users can right-click any nav item and "Pin to top" — creating a personalized quick-access section above the navigation groups. Pinned items are stored in localStorage and sync to the user profile.

**Nav filter bar**: A mini search input at the top of the nav (only in expanded state). Typing filters visible nav items in real time, including pinned views and saved searches. This is how power users navigate enormous workspaces — not by scrolling, but by typing.

### 2.4 Workspace Switcher

The workspace switcher serves organizations with multiple environments (e.g., IT, HR, Facilities operating as separate workspaces under one account).

**Trigger**: Click the workspace name/chevron in the top-left, or press `⌘ + Shift + W`.

**Appearance**: A 280px × variable-height popover, appearing below the trigger with a 4px offset. Background: `#1E293B` in dark mode. The list items show workspace avatar (24px, auto-generated colored initials), workspace name, user's role in that workspace, and an unread badge if there are new items.

**Switching animation**: When a workspace is selected, the content area performs a subtle `opacity: 0 → 1` fade (150ms) while the navigation items morph to the new workspace's structure. The top bar workspace name updates in place with a `scale(0.95) → scale(1)` spring animation.

### 2.5 Command Palette — ⌘K System

The command palette is the single most important productivity surface in the product. It is how power users do 60% of their navigation and actions.

**Trigger**: `⌘K` (Mac), `Ctrl+K` (Windows/Linux), or click the global search bar.

**Appearance**: A 640px wide modal, vertically centered at 30% from top (not 50% — slightly high to avoid the user's natural reading eye level). Background: `#1E293B` with `box-shadow: 0 32px 64px rgba(0,0,0,0.5)`. Overlay: `rgba(0,0,0,0.6)` backdrop with blur.

**Anatomy**:
```
┌──────────────────────────────────────────────────────────────┐
│ 🔍  [type to search or use a command...]              ⌘K ×  │
├──────────────────────────────────────────────────────────────┤
│ RECENT                                                        │
│  🎫 TKT-1847  VPN access issue - Marketing     2m ago        │
│  🎫 TKT-1843  Printer offline - Floor 3       15m ago        │
│  📄 Password reset guide                       1h ago        │
├──────────────────────────────────────────────────────────────┤
│ QUICK ACTIONS                                                 │
│  ＋ New Ticket                              ⌘N               │
│  ＋ New KB Article                          ⌘⇧N             │
│  📊 View Dashboard                          ⌘D               │
│  ☀️  Toggle Theme                           ⌘⇧L             │
└──────────────────────────────────────────────────────────────┘
```

**After typing** (e.g., typing "vpn"):
```
┌──────────────────────────────────────────────────────────────┐
│ 🔍  vpn                                               ⌘K ×  │
├──────────────────────────────────────────────────────────────┤
│ TICKETS  (4 results)                              See all →  │
│  🔴 TKT-1847  VPN access issue - Marketing    HIGH  open     │
│  🟡 TKT-1831  VPN timeout - Remote team       MED   open     │
│  ✅ TKT-1798  VPN configuration               LOW  closed    │
│  ✅ TKT-1765  VPN certificate renewal          HIGH closed   │
├──────────────────────────────────────────────────────────────┤
│ KNOWLEDGE BASE  (2 articles)                                  │
│  📄 VPN Setup Guide (updated 3 days ago)                     │
│  📄 VPN Troubleshooting — Common Errors                      │
├──────────────────────────────────────────────────────────────┤
│ AGENTS  (1 match)                                             │
│  👤 VPN Team • 3 members                                     │
└──────────────────────────────────────────────────────────────┘
```

**Natural language queries**: The palette understands intent phrases:
- "my open tickets" → filters to current user's assigned open tickets
- "overdue today" → opens filtered queue: past-SLA tickets
- "assign TKT-1847 to Ali" → opens assignment modal with Ali pre-filled
- "mark TKT-1847 resolved" → confirmation toast: "Mark TKT-1847 as resolved? Enter to confirm"

**Navigation within palette**: `↑/↓` to navigate, `Enter` to activate, `Tab` to switch sections, `Esc` to close (returns focus to exact previous location).

### 2.6 Global Notification Center

**Trigger**: Bell icon in top chrome. Badge shows unread count.

**Appearance**: 400px wide slide-over panel from the right, 100% viewport height, does NOT displace content (overlaps). Opening animation: `translateX(400px) → translateX(0)` over 250ms with `cubic-bezier(0.4, 0, 0.2, 1)`. Background: `#1E293B` in dark mode, separated from content by a left `1px` border.

**Notification item anatomy** (72px minimum height):
- Left: 8px color-coded border indicating category (red = urgent, amber = warning, blue = info, green = resolved)
- 8px padding
- Icon (notification type, 20px) + unread indicator (8px filled circle, `#6366F1`)
- Title (14px/medium, max 2 lines)
- Meta line: source entity → age → actor
- Right: action buttons that appear on hover (e.g., "Open", "Dismiss") — 28px height, ghost variant

**Grouping**: Notifications are grouped by time (Today, Yesterday, This Week, Earlier). Within Today, they're grouped by ticket — if 4 notifications all relate to TKT-1847, they collapse into a single grouped item that expands on click.

**Mark all read**: A button in the panel header. Visual feedback: all unread dots fade out in a staggered animation (each item 20ms offset, creating a ripple effect).

**Notification preferences**: A gear icon in the panel header opens a slide-over *within* the notification panel (not a new modal) — a nested slide-over at 360px. Users can mute categories, set delivery preferences, and configure quiet hours.

### 2.7 Visual Design Direction — The Detail Layer

**Surface hierarchy** (dark mode, 5 levels):
```css
--surface-base:    #080B10;  /* Page background */
--surface-1:       #0F172A;  /* Primary containers */
--surface-2:       #1E293B;  /* Cards, panels, modals */
--surface-3:       #263245;  /* Hover states, selected */
--surface-4:       #334155;  /* Active states, separators */
```

**Elevation system** (shadows, not borders for depth):
```css
--shadow-sm:  0 1px 2px rgba(0,0,0,0.4);           /* Cards */
--shadow-md:  0 4px 12px rgba(0,0,0,0.4);           /* Popovers */
--shadow-lg:  0 16px 32px rgba(0,0,0,0.5);          /* Modals */
--shadow-xl:  0 32px 64px rgba(0,0,0,0.6);          /* Command palette */
```

**Border system**: Borders are used only for separation, never decoration. All borders are `1px solid var(--surface-4)` — no 2px borders anywhere except active nav indicators. Border radius:
```css
--radius-sm:  4px;   /* Tags, badges, small chips */
--radius-md:  6px;   /* Buttons, inputs, small cards */
--radius-lg:  10px;  /* Cards, panels */
--radius-xl:  14px;  /* Modals, slide-overs */
--radius-full: 9999px; /* Pills, avatars */
```

**Hover states**: Every interactive element has a hover state that:
1. Changes background (never just cursor change)
2. Transitions in 100-150ms (fast enough to feel snappy, slow enough to be intentional)
3. Never moves the element (no `transform: scale` on hover — it breaks visual flow)

**Focus states**: 2px offset outline in `#6366F1` (indigo) with `border-radius` matching the element. This is universally applied, never suppressed with `outline: none` unless replaced by an equivalent visible focus indicator.

### 2.8 Typography Hierarchy — Applied

```
Level 0 — Page title:          Staatliches 32px, #F8FAFC, tracking -0.5px
Level 1 — Section heading:     IBM Plex Sans 20px/600, #F1F5F9
Level 2 — Card heading:        IBM Plex Sans 16px/600, #E2E8F0
Level 3 — Body/Labels:         IBM Plex Sans 14px/400, #CBD5E1
Level 4 — Meta/Captions:       IBM Plex Sans 12px/400, #94A3B8
Level 5 — Micro/Legal:         IBM Plex Sans 11px/400, #64748B

Monospace — IDs, code, counts: IBM Plex Mono 13px/400, #94A3B8
```

**Line height rules**:
- Display text: 1.1
- Headings (16px+): 1.25
- Body text (14px): 1.5
- Dense UI text (12px): 1.4

### 2.9 Card Design Language

Cards are the primary information containers. Three card variants:

**Flat card** (ticket list items, search results):
- Background: `--surface-2`
- Border: `1px solid --surface-4`
- Padding: `12px 16px`
- No shadow — shadow reserved for elevated content
- Hover: `background: --surface-3`, transition 100ms
- Left accent strip (4px wide, full height) color-coded by status or priority

**Raised card** (dashboard widgets, KPI cards):
- Background: `--surface-2`
- Border: `1px solid --surface-4`
- Shadow: `--shadow-md`
- Padding: `20px 24px`
- On hover: shadow elevates to `--shadow-lg`, transition 200ms

**Interactive card** (workflow steps, service catalog items):
- As raised card, plus:
- Cursor `pointer`
- Hover shifts background to `--surface-3` AND elevates shadow
- Press (`:active`): shadow reduces back to `--shadow-sm` for tactile feedback

### 2.10 Loading States & Skeleton Loaders

**Skeleton design**: Animated gradient sweep (`background: linear-gradient(90deg, --surface-2 0%, --surface-3 50%, --surface-2 100%)`) animating at 1.5s/infinite. Skeleton shapes exactly mirror the content they represent — a 2-line ticket title skeleton is exactly 2 lines at the correct widths.

**Skeleton timing**: Skeletons appear only after 150ms delay. If content loads in < 150ms, skeletons never appear — this prevents flickering for fast connections.

**Progressive loading**: In a ticket list, the first 5 items load at full quality. Items 6–20 load at 80% quality (images at lower resolution, avatar placeholders). Items below fold are not loaded until scroll approaches.

**Inline loading**: When an action triggers a server request (e.g., changing ticket status), the element itself shows a spinner overlay — `position: absolute` on the button, `background: rgba(--surface-2, 0.7)`, with a 16px spinner. The element is disabled but its size doesn't change. This eliminates layout shift.

### 2.11 Micro-Interactions Catalog

**Status badge transition**: When a ticket status changes, the badge doesn't simply update. It performs: shrink (`scale(0.8)`) → background crossfade (new color) → expand back (`scale(1.0)`) → brief glow pulse of the new color. Duration: 400ms total. Easing: spring.

**Notification bell**: When a new notification arrives, the bell icon performs: `rotate(-15deg) → rotate(15deg) → rotate(-10deg) → rotate(0deg)` — a bell-ringing animation, 500ms. The count badge scales in from `scale(0)` simultaneously.

**Drag-and-drop**: When a ticket card is picked up for drag:
- The original position shows a dashed placeholder of the same dimensions
- The dragged card gets `box-shadow: --shadow-xl` and slight `scale(1.02)` — the "picked up" state
- Valid drop targets highlight with `border: 2px dashed #6366F1` and background `rgba(99, 102, 241, 0.05)`
- Drop: the card springs into place with a `scale(1.02) → scale(1.0)` bounce, 200ms

**Command palette open**: Overlay fades in (150ms), palette scales from `scale(0.97) translateY(-8px)` to `scale(1) translateY(0)` in 200ms with spring easing. The input auto-focuses immediately.

**Toast notifications**: Appear from bottom-right, sliding up from `translateY(16px) → translateY(0)` with `opacity: 0 → 1`. Auto-dismiss after 4 seconds (success) or 8 seconds (error, to ensure reading time). On hover, the dismiss timer pauses. Max 3 toasts visible simultaneously; oldest dismisses when a 4th appears.

---

## 3. Ticket Management UX

### 3.1 The Ticket Queue — Three Layout Modes

The queue is the agent's home. Agents spend 70%+ of their time here. Every pixel of the queue is earned.

**Mode switcher**: Three icons in the toolbar — Table (default), Board (Kanban), Timeline. Mode persists per user across sessions.

#### 3.1.1 Table View (Default)

A high-density, keyboard-navigable data table. NOT a standard HTML table — a virtualized list rendering only visible rows (handles 10,000+ tickets without performance degradation).

**Column configuration**:
- Default columns: Priority dot | ID | Title | Status | Assignee | Department | Created | SLA countdown
- Users drag column headers to reorder
- Click column header to sort (ascending → descending → unsorted, cycling)
- Column widths are draggable and remembered per user
- Right-click column header: "Hide column", "Pin left", "Pin right", "Add column"

**Row design** (40px height, density: standard):
```
[Priority] [TKT-ID] [Title — truncated, expands on hover] [Status badge] 
[Assignee avatar + name] [Department chip] [Created] [SLA bar]
```

**SLA Bar**: A thin progress bar at the right edge of each row (not a number — a visual indicator). Width: 64px. Color: green (>50% remaining) → amber (20-50%) → red (<20%) → pulsing red (<10% or breached). The bar fills left-to-right representing time elapsed. On hover: a tooltip shows exact remaining time and breach date/time.

**Row hover state**: Background lightens to `--surface-3`. A subtle action toolbar slides in from the right edge: [Quick Assign] [Change Status] [Add to Bulk]. These are 24px icon buttons — never visible at rest, appearing only on hover to keep the table clean.

**Row selection**: Click to select single ticket (highlights row, opens detail in right panel). `Shift+click` to select range. `Ctrl/⌘+click` to add to selection. `⌘+A` selects all visible tickets. Selected rows show a `#6366F1` left border and slightly elevated background.

**Keyboard navigation**:
- `J` / `↓` — next ticket
- `K` / `↑` — previous ticket
- `Enter` — open selected ticket detail
- `X` — toggle selection on focused ticket
- `O` — open ticket in full view
- `E` — inline-edit ticket title
- `/` — focus filter bar
- `G then Q` — go to queue (chord navigation)

**Density toggle**: Three density modes in the toolbar — Compact (32px rows), Standard (40px rows), Comfortable (52px rows). Standard is default; compact is for power users managing large queues; comfortable for users who prefer more whitespace.

#### 3.1.2 Kanban Board View

**Board structure**: Each column represents a status. Columns are 280px wide, with a `12px` horizontal scroll gap. The board scrolls horizontally if columns exceed viewport.

**Column headers**:
- Status name (16px/600)
- Ticket count badge (right-aligned)
- Column total (if the column has tickets with quantifiable values)
- `+` button to create a new ticket directly in this status

**Card design** (Kanban):
```
┌───────────────────────────────────────────────┐
│ [Priority dot] [TKT-1847]            [•••]    │
│ VPN access issue for Marketing team           │
│ ──────────────────────────────────────────── │
│ [IT Dept] [🔴 HIGH]           [SLA: 1h 23m]  │
│ [👤 A. Ben Ali]                    [2 💬 3📎] │
└───────────────────────────────────────────────┘
```

**Card hover**: Elevates with `--shadow-lg`, shows a "Quick actions" row — four icon buttons: Assign, Priority, Comment, Resolve.

**Drag between columns**: When dragging a card between status columns, a status-change confirmation is not required for standard transitions. Only for irreversible transitions (e.g., Closed → Open) does a single-line inline confirmation appear. This eliminates 80% of confirmation dialogs.

**Collapsed columns**: Columns with no tickets show as 40px wide vertical labels (text rotated 90°) — they collapse to save horizontal space but remain visible for drag-and-drop targets.

#### 3.1.3 Timeline View

For managers monitoring SLA and scheduling:

- Horizontal axis: time (day/week/month, selectable)
- Vertical axis: agents or departments (grouped rows)
- Each ticket is a horizontal bar spanning its open duration
- Bar color codes status
- SLA deadline marked as a vertical line on each bar
- Bars that have breached SLA have a red hatch pattern

**Interactions**: Hover a bar for tooltip with full ticket details. Click to open ticket. Drag a bar's right edge to request SLA extension (sends a SLA extension request, doesn't change unilaterally). Zoom in/out with `Ctrl+Scroll`.

### 3.2 Smart Filtering System

**Filter bar**: Appears below the toolbar, collapsible (default: expanded if filters are active, collapsed if none). A horizontal row of filter pills.

**Quick filters** (always visible, pre-built):
- "Mine" — assigned to current user
- "Unassigned" — no assignee
- "SLA at risk" — P(breach) > 0.6
- "New today" — created in last 24h
- "Needs reply" — awaiting agent response
- "Overdue" — past SLA deadline

**Advanced filter builder**: Clicking "+ Add filter" opens a filter popover:
1. Select attribute (dropdown with search): Status, Priority, Assignee, Department, Category, Created, Modified, Reporter, Tag, Custom fields...
2. Select operator: is, is not, is any of, contains, is before, is after...
3. Enter value (context-appropriate input: date picker for dates, user picker for assignee, etc.)
4. Click "Apply" — the filter pill appears in the bar

**Saved views**: Any combination of filters + sort + layout mode can be saved as a named view. Views appear in:
1. The sidebar under the nav item they belong to (with count badge)
2. A "Views" section at the top of the filter bar
3. The command palette under "Views"

Named views can be shared with the team or kept personal.

**Filter chip design**: 28px height, `border-radius: --radius-full`, background `rgba(99, 102, 241, 0.15)`, text `#A5B4FC`. Hovering reveals an `×` to remove. Clicking opens the filter editor popover for that filter.

### 3.3 Ticket Creation Flow — Redesigned

**Entry point**: `⌘N` from anywhere, `+ New Ticket` button in the nav, or `+` in a Kanban column.

**Creation modal**: 680px wide, max-height 80vh, vertically scrollable. Opens with a 200ms scale-in animation.

**The form — progressive revelation**:

**Stage 1 — Intent capture** (always visible):
```
What needs to be resolved?
┌─────────────────────────────────────────────────────────────────┐
│ [Subject line — large, 20px, auto-focused]                     │
└─────────────────────────────────────────────────────────────────┘
```
As the user types, AI analyzes the title in real time (debounced 600ms). After the user types ≥ 6 words, AI suggests:
- Category (with confidence score)
- Priority (with reasoning)
- Potentially related open tickets (prevents duplicate creation)

This appears as a subtle suggestion bar below the title:
```
✨ AI suggests:  Category: Network • Priority: High  |  Why?  |  Apply
```

**Stage 2 — Category selection**: A visual category picker (not a dropdown) — 2-column grid of category cards with icon and name. The AI-suggested category is highlighted. Users can override. Selecting a category triggers Stage 3.

**Stage 3 — Dynamic contextual fields**: Each category has a configured field set. Selecting "Network / VPN" shows different fields than "HR / Onboarding". Fields animate in from the bottom over 200ms (staggered, 30ms per field). Standard fields:
- Description (rich text editor — see §3.5)
- Affected user (if different from reporter)
- Priority (AI-suggested, overridable)
- Attachment drop zone

**Stage 4 — Confirmation summary** (appears after all required fields filled):
A compact summary card at the bottom of the form:
```
🎫 Creating ticket in IT / Network
   Priority: High (AI suggested) | Assignee: Auto-route | SLA: 4h response
   [ Create Ticket ]   [ Save as Draft ]
```

**Submission**: `⌘Enter` submits from any field. After submission, the modal closes and the new ticket appears in the queue via optimistic insert — no page reload, no spinner wait. A success toast appears: "TKT-1848 created — [Open ticket ↗]".

### 3.4 Ticket Detail View — The Redesigned Workspace

The single most visited screen. Layout: three panels, always visible on desktop ≥ 1280px.

```
┌────────────────────────────────────────────────────────────────────────┐
│  [← Back]  TKT-1847  •  VPN access issue for Marketing  [⋯ actions]   │
├──────────────────────┬──────────────────────────┬──────────────────────┤
│                      │                          │                      │
│   LEFT PANEL         │    CENTER THREAD         │   RIGHT CONTEXT      │
│   (280px)            │    (flexible)            │   (320px)            │
│                      │                          │                      │
│   Ticket metadata    │    Ticket description    │   Reporter card      │
│   Status controls    │    ──────────────────    │   ──────────────────  │
│   Assignee           │    Comment thread        │   AI insights        │
│   Priority           │    (chronological)       │   ──────────────────  │
│   SLA timer          │    ──────────────────    │   Related tickets    │
│   Department         │    Reply composer        │   ──────────────────  │
│   Category           │                          │   SLA details        │
│   Tags               │                          │   ──────────────────  │
│   Linked tickets     │                          │   History            │
│   Attachments        │                          │                      │
│                      │                          │                      │
└──────────────────────┴──────────────────────────┴──────────────────────┘
```

**Left panel — Ticket metadata**:

Each metadata field is *inline editable* — clicking any value opens an inline editor in place (no modal, no navigation). The edit mode is a subtle background highlight + cursor change. Saving is automatic on `Enter` or click away.

Status field: A large, prominent status chip at the top of the left panel (full width of the panel). Clicking it opens a status transition picker — not a dropdown, but a visual flow showing all valid next states with one-click transition. The current status glows faintly in its semantic color.

SLA Timer: A circular progress ring (40px diameter) showing time remaining as a sweeping arc. Center text: remaining time in appropriate unit ("2h 14m" or "3 days"). Color: green → amber → red as time reduces. On breach: ring stops, center shows "BREACHED", color pulses red every 3 seconds.

Priority selector: Five colored dots in a row (low → critical). The active priority dot is 12px, inactive are 8px. Click to change. The selected dot has a concentric ring halo in its priority color.

**Center panel — Thread**:

The thread is a chronological conversation view — alternating between the reporter (left-aligned messages, avatar, name) and agents (right-aligned, agent avatar, name). This visual differentiation is critical — agents and reporters are instantly distinguishable without reading names.

Internal notes: Rendered with a `rgba(245, 158, 11, 0.08)` amber-tinted background and a left `3px` amber border. A "INTERNAL" label appears at the top-left of internal note cards. These are invisible to the reporter.

**Comment composer** (always visible at the bottom of the center panel):
```
┌─────────────────────────────────────────────────────────────────────┐
│  [🖊 Reply] [🔒 Internal Note] [📞 Log Call]        (3 tabs)        │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                             │   │
│  │  Type a response... (or press Tab for AI draft)            │   │
│  │                                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  [B] [I] [<>] [🔗] [📎]  @mention  #ticket  /kb        [Send ⌘↵]  │
└─────────────────────────────────────────────────────────────────────┘
```

The `Tab` key behavior: pressing Tab in an empty reply box triggers AI draft generation. The draft text *types itself* character by character at approximately 400 chars/second (fast enough to feel instant, slow enough to communicate that AI is working). The typewriter effect serves as both a loading animation and a readability aid. The cursor blinks at the end of the typing. After completion, a subtle AI badge appears below the draft: "✨ AI drafted · 87% confident · Edit freely · [Why?]".

**Right panel — Context**:

**Reporter card**: Avatar (48px), name, role, email, department, and a mini-history: "Previously: 12 tickets | Avg resolution: 2.1h | CSAT: 4.7/5 | Last contact: 2h ago". A VIP indicator (star) appears if the reporter is flagged as VIP.

**AI Insights card** (indigo-tinted background):
```
✨ AI CONTEXT

🔍 Root Cause: VPN gateway update deployed at 14:30 
   today (3h before this ticket). 4 similar tickets.
   
📋 Suggested Resolution:
   See KB #847 — VPN Gateway Post-Update Fix
   [Apply macro →]
   
⚡ Related Open Tickets: 4 from same department
   [View cluster →]
```

**History tab** (in right panel): A minimal timeline — each entry is a single line: icon + action + actor + timestamp. No card, no border — pure list density. Grouped by session (all actions within 30 minutes grouped under the first action's timestamp).

### 3.5 Rich Text Editor — Cosmitto Compose

A bespoke rich text editor built for support workflows (not a general-purpose editor).

**Toolbar** (appears on text selection, not fixed at top):
A floating toolbar that appears 8px above the selection: Bold, Italic, Code, Link, Heading (H2/H3 only — no H1 in ticket content), Blockquote, Bulleted list, Numbered list, Mention, KB-link.

**Slash commands**: Type `/` at the start of a line to open a command menu:
- `/kb` — embed a KB article reference inline
- `/ticket` — link to another ticket
- `/template` — insert a response template
- `/bullet` — start a bullet list
- `/code` — insert code block
- `/image` — insert image (from uploads or clipboard paste)

**@mentions**: Typing `@` opens a user picker (filtered as you type). Mentioned users receive a notification. Mentions are rendered as chips in the sent message.

**Paste behavior**: Pasting an image from clipboard auto-uploads it and inserts inline. Pasting a URL detects if it's a known ticket ID or KB article and offers to convert it to a rich link embed.

### 3.6 Bulk Actions Experience

Entering bulk mode: selecting 2+ tickets activates the bulk action bar — it slides up from the bottom of the viewport, replacing the status bar area.

**Bulk action bar design**:
```
┌────────────────────────────────────────────────────────────────────┐
│  ■ 7 tickets selected  [Clear]                                     │
│  [Assign] [Status] [Priority] [Tag] [Macro] [Export] [Delete]     │
└────────────────────────────────────────────────────────────────────┘
```
Height: 56px. Background: `#1E3A5F` (dark navy accent). Slides in from bottom with spring animation. Position: `position: fixed, bottom: 0`.

**Assign action** (in bulk context): Opens a popover with an agent list. Shows each agent's current queue depth next to their name — "Ali Ben Ali (12 open)", "Sara Mansour (4 open)". Green/amber/red dots indicate workload health. This lets managers make informed assignment decisions without opening separate screens.

**Bulk status change**: Opens a compact status picker. A preview shows "This will change 7 tickets to [Status]. 2 tickets have active SLAs that will be affected." — surfacing consequences without blocking the action.

---

## 4. Dashboard & Analytics UX

### 4.1 Dashboard Architecture — Personalized Intelligence Hub

Every user sees a different dashboard based on their role:
- **Agent**: Personal workload + team queue health
- **Manager**: Team performance + SLA compliance + escalation watch
- **Admin**: Operational metrics + system health + user activity
- **Executive**: Business KPIs + trend lines + forecast summaries

### 4.2 Executive Dashboard

**The "1-minute board review" layout** — all key information visible without scrolling on a 1440×900 screen.

**Row 1 — Hero KPIs** (5 cards, equal width):
Each KPI card design:
```
┌──────────────────────────────┐
│  📊  OPEN TICKETS            │
│                              │
│  247                        │
│  [Staatliches, 48px]        │
│                              │
│  ↑ 12% vs last week         │
│  [green/red trend chip]     │
└──────────────────────────────┘
```
The trend number is always context-interpreted: +12% in open tickets is red (bad), +12% in resolved tickets is green (good). The color logic is built into the metric configuration, not left to raw arithmetic.

Micro-chart: A 40px-tall sparkline runs along the bottom of each KPI card, showing the last 14 days' trend. Hover over the sparkline shows a tooltip with the exact daily value.

**Row 2 — Operational Matrix** (2 large widgets, 1 medium widget):
- **Ticket volume heatmap** (2/3 width): 7×24 grid (days × hours). Each cell is colored by volume intensity (white → light blue → deep blue → red). Hovering a cell shows: "Tuesday 14:00-15:00: Average 23 tickets, 3x baseline". This tells managers exactly when to staff up.
- **Status distribution** (1/3 width): A horizontal stacked bar — proportional representation of all open tickets by status. Each segment is labeled with count. Clicking a segment filters the main queue to that status.

**Row 3 — Performance & Forecast** (3 equal widgets):
- **Agent leaderboard**: Top 5 agents by resolved count (this period). Each row: avatar, name, count, CSAT star rating, small bar showing utilization. A "vs last period" delta.
- **SLA compliance gauge**: A half-circle gauge (like a speedometer) showing current SLA compliance rate. 0-100%. Color zones: 0-70% red, 70-85% amber, 85-100% green. Below the gauge: "Target: 95% | Current: 91.3% | Trend: ↑2.1%"
- **Volume forecast widget**: A line chart showing actual volume (solid line) and predicted volume (dashed line) for the next 48 hours. Confidence interval shown as a shaded band. Below: "Peak predicted: Tomorrow 14:00-16:00. Recommend: +2 agents."

**Widget customization**: Hover any widget → a `⋯` button appears top-right → menu: "Resize", "Move", "Configure", "Replace", "Remove". The dashboard enters "edit mode" with a grid overlay when any widget is being moved. Edit mode is explicit (a banner confirms "Dashboard edit mode — drag to rearrange") and exits on "Save layout" or "Cancel".

### 4.3 Agent Personal Dashboard

**Above the fold** — "Your day at a glance":
```
Good morning, Ali ☀️
You have 14 open tickets · 3 need attention · 2 SLAs expiring soon
```
The greeting message is personalized and changes across the day. The "3 need attention" link opens a filtered view of only those tickets.

**My Queue** (primary widget, 2/3 width): The agent's assigned tickets, sorted by SLA urgency. Not a full table — a compact list widget showing the top 8 tickets with priority, ID, title, status, and SLA countdown. "Open full queue →" link at the bottom.

**Today's Stats** (1/3 width): A mini-scorecard showing: Resolved today (with goal if set), Average response time, CSAT today, and a streak indicator ("🔥 3-day CSAT ≥4.8 streak").

**AI Coaching Insight** (bottom strip): A single insight from Coach AI:
```
💡 Ali's tip of the day
Your "Network" ticket response time is 2.4h vs your team's 1.1h average.
KB article #847 could help — it covers 71% of your Network ticket types.
[Open article →]  [Dismiss]
```

### 4.4 Interactive Chart Design Principles

**Chart library**: D3.js-powered custom charts — never a third-party chart library whose visual style can't be controlled. Charts adhere to the Cosmitto design system perfectly.

**Chart color palette** (accessible, color-blind safe):
```css
--chart-1: #6366F1;  /* Indigo — primary series */
--chart-2: #0EA5E9;  /* Sky — secondary series */
--chart-3: #10B981;  /* Emerald — positive */
--chart-4: #F59E0B;  /* Amber — caution */
--chart-5: #EF4444;  /* Red — negative/urgent */
--chart-6: #8B5CF6;  /* Violet — 6th series */
```

**Universal chart behaviors**:
- All charts have hover tooltips (not click tooltips — hover for accessibility)
- Tooltips: 8px offset from cursor, instant appear, 200ms fade out
- All axes are labeled (no chart without axis labels)
- All charts have accessible data tables hidden off-screen (for screen readers)
- Animations play only on first load (not on hover or filter changes, which are instantaneous)

**Axis design**: No outer border. Grid lines are `1px dashed rgba(255,255,255,0.07)` — barely visible, providing reference without adding visual weight. Axis labels: 11px/IBM Plex Mono, `--text-muted`.

**Chart interactivity**:
- Click a line chart data point: opens a modal with drill-down data
- Click a bar in a bar chart: applies that value as a filter on the ticket queue
- Click a pie/donut segment: same filter behavior
- "Brush selection" on time-series: drag across a date range to zoom in

### 4.5 Real-Time Dashboard Indicators

**Live data indicators**: Any widget showing live data has a subtle pulsing dot (8px, `#10B981`, 2s pulse animation) in its top-right corner. Hovering the dot shows "Updated 12 seconds ago · Refreshes every 30s".

**Update animation**: When a KPI number changes due to a live update:
1. The number scales slightly (`scale(1.0) → scale(1.05) → scale(1.0)`, 300ms)
2. If number increased: briefly flashes green background on the card
3. If number decreased: briefly flashes red background
4. The sparkline redraws with the new data point, with the new point animating in from the right

**"Something just changed" notification**: If a watched metric crosses a threshold while the dashboard is on screen (not in a background tab), a banner appears above the widget: "⚠ SLA compliance just dropped below 90% · View affected tickets →"

---

## 5. AI-Powered UX

### 5.1 AI Copilot — The Ambient Intelligence Layer

The AI copilot is not a chatbot sidebar. It is the invisible intelligence layer that makes every interaction smarter. When it surfaces, it does so in context, with restraint.

**Rule of AI UX**: AI only surfaces when it has something genuinely useful to offer AND the user is in a state where they can act on it. Never interrupt mid-flow.

### 5.2 Inline AI Reply Generation

Triggered by pressing `Tab` in an empty reply composer (see §3.4). The behavior:

1. `Tab` pressed in empty reply box
2. A subtle "✨ Generating..." label appears in the composer area (12px, `#A5B4FC`, italic)
3. After 200–800ms (actual generation time), text begins appearing via typewriter animation
4. The typewriter speed adapts to the text length — short responses type faster
5. Generation can be interrupted with `Esc` — the partial text remains and the typewriter stops
6. On completion: the cursor positions at the end of the text for immediate editing
7. Below the draft: `✨ AI drafted · 87% confident · [Edit] [Accept ⌘⇧Enter] [Regenerate ⌘⇧R] [Why? →]`

**"Why?" expansion**: Clicking "Why?" expands a 160px panel below the draft:
```
AI drafted this response because:
• KB article #847 matches this ticket type (94% relevance)
• Ali resolved 12 similar VPN tickets — this matches his
  top-used resolution approach
• Reporter has basic technical level (detected from message)
  — response uses simplified language
```

**AI confidence visual**: A thin horizontal bar below the draft text (2px height, `border-radius: 1px`). Color: green (>80%), amber (60-80%), red (<60%). This is the only visual indicator of confidence — subtle, not alarming.

### 5.3 Smart Auto-Tagging

**Behavior**: After a ticket is created or a description is updated, tags appear as suggestions below the tag field within 1–2 seconds:

```
Suggested tags:  [VPN] [Network] [Remote Work] [Priority-High]
                 ✓ Accept all     Accept individually
```

Each suggested tag shows a mini-confidence indicator (opacity of the chip correlates to confidence — high confidence chips are fully opaque, low confidence are semi-transparent). This visual encoding communicates certainty without numbers.

**Accepting**: Click "Accept all" → all chips animate from suggestion state (dashed border) to accepted state (solid border) in a staggered animation (40ms per chip). Individual acceptance: click a chip to accept it, cross to dismiss.

### 5.4 AI Ticket Summarization

For long tickets with 20+ comments: a "Summary" button appears above the thread.

**Summary panel design** (slides down below the ticket header, above the thread):
```
┌─────────────────────────────────────────────────────────────────┐
│  ✨ AI SUMMARY  ·  Generated from 23 messages             [×]  │
├─────────────────────────────────────────────────────────────────┤
│  Issue: User unable to connect to VPN after office             │
│  network migration on May 18th.                                │
│                                                                 │
│  Attempts: IT team tried 3 configurations. Client-side        │
│  reinstall attempted twice. Root cause identified as           │
│  firewall rule in VLAN-12 (by agent Sara Mansour, May 19).    │
│                                                                 │
│  Current status: Fix deployed. Awaiting user confirmation.    │
│                                                                 │
│  ⚡ Recommended next action: Follow up for resolution          │
│     confirmation. SLA expires in 1h 43m.                      │
└─────────────────────────────────────────────────────────────────┘
```

The panel is collapsible (persists collapsed state per ticket per user). It appears above the thread so agents get context before reading the full history.

### 5.5 AI-Powered Search Experience

**Search results page** redesigned as an intelligence layer:

**Query understanding**: When a user searches "VPN tickets last week unresolved", the search bar renders the query as parsed tokens:
```
[VPN] tickets [last week] [unresolved]
```
Each token is a chip — clicking a chip opens an editor for that filter. This makes the query legible and editable.

**Result ranking**: Results are ranked by relevance + recency + user interaction history (tickets the user has viewed/worked on rank higher for the same user).

**AI answer card** (appears at top of results when confidence > 0.8):
```
┌─────────────────────────────────────────────────────────────────┐
│  ✨ AI Answer                                                   │
│                                                                 │
│  There are 7 unresolved VPN tickets from last week.            │
│  5 are assigned to the IT Network team. 2 are overdue.        │
│  The most common issue is post-migration firewall config.      │
│                                                                 │
│  [View all 7 tickets →]  [View overdue 2 →]                   │
└─────────────────────────────────────────────────────────────────┘
```

### 5.6 SLA Risk AI Warnings

**Warning presentation**: When AI predicts P(SLA breach) > 0.65, a warning manifests in three locations simultaneously:
1. **In the queue list**: The SLA bar becomes pulsing red; an amber alert icon appears inline
2. **In the notification center**: A warning notification is pushed immediately
3. **In the ticket detail**: A warning banner slides down from the top of the center panel:

```
⚠ SLA BREACH PREDICTED
This ticket has a 73% chance of breaching SLA in 1h 15m.
AI recommends: [Reassign to Sara (available)] or [Extend SLA] or [Escalate]
                                                              [Dismiss]
```

Each recommended action is a button — one click executes it (with confirmation for destructive/escalation actions).

### 5.7 AI Workflow Suggestions

On the workflow builder canvas (see §9), AI can suggest automations based on observed patterns:

**Discovery banner** (appears in workflow builder):
```
💡 CosmittoAI detected a pattern in your data

67 tickets of type "Password Reset" are always resolved using
the same macro. An automation could handle this automatically.

Estimated impact: ~4h/week saved for your team.

[Preview automation →]  [Create workflow →]  [Dismiss]
```

Clicking "Preview automation" shows the proposed workflow in a read-only view on the canvas — the user can then activate it with one click or customize it first.

---

## 6. Knowledge Base UX

### 6.1 The Knowledge Base Philosophy

The KB is not a documentation folder. It is a **living operations memory** — the organizational brain that gets smarter with every resolved ticket. The UX must make contributing to it frictionless (so agents actually do it) and finding information in it effortless (so they actually use it).

### 6.2 KB Homepage Design

**Three-zone layout**:

**Zone 1 — Search** (prominent, centered, hero):
A large, centered search bar (480px wide, 52px tall) with placeholder "Search knowledge base..." The search is semantic — typos, synonyms, and partial phrases all work. Below the search bar: recent searches + AI-suggested articles based on current open tickets.

**Zone 2 — Category navigation** (below search):
A visual category grid — 2 columns on desktop, cards with:
- Category icon (32px, colored by category)
- Category name (18px/600)
- Article count (14px/muted)
- Top 3 articles listed below (14px links)

**Zone 3 — Featured & Recent** (right sidebar on desktop):
- "Most viewed this week" (ranked list, 5 items)
- "Recently updated" (with delta: "Updated 2 days ago")
- "Contribute to KB" CTA — prominently placed: "📝 Convert a resolved ticket → Article"

### 6.3 Article View — Cosmitto Docs Experience

**Reader layout**: Max-width 740px, centered, with a generous right sidebar (240px) for navigation.

**Right sidebar content**:
- "On this page" table of contents (auto-generated from headings) — sticky, with active section highlighted as user scrolls
- Article metadata: author, last updated, version
- "Was this helpful?" (two-button: 👍 / 👎) — always visible without scrolling
- Related articles (3 items, AI-suggested)
- "Actions" (for agents with edit permissions): Edit, Share link, Report issue, Convert to template

**Reading progress**: A 2px progress bar at the top of the viewport (full width, `--cosmitto-red`) shows reading progress. Unlike most implementations, this progress bar does NOT advance based on scroll position but on estimated reading time for visible content — this is more accurate for readers who pause to follow steps.

**Code blocks**: Syntax highlighted, copy-to-clipboard button, language label. Long code blocks are collapsible (> 20 lines auto-collapse with "Expand code block ↓" link).

**Step-by-step procedures**: Articles with numbered steps use a special rendering — each step has a large step number in `--cosmitto-red`, a heading, and indented content. The currently-in-progress step can be checked off (checkbox that persists in localStorage — so if an agent leaves and returns, their progress is saved).

### 6.4 Article Editor — The Cosmitto Docs Editor

**Not a WYSIWYG block editor**. A hybrid: clean prose in the center, blocks (like Notion) for structured content.

**Editor toolbar** (floating, appears on block hover or text selection):
```
[H1] [H2] [H3] | [B] [I] [U] [S] | [Link] [Code] | [Align] | [⋮ more]
```

**Block types available**:
- Paragraph (default)
- Heading (H2, H3 — H1 is the article title)
- Bullet list / Numbered list
- Checklist (for step-by-step procedures)
- Code block (with language selector, syntax highlighting)
- Warning callout (amber background, ⚠ icon)
- Info callout (blue background, ℹ icon)
- Tip callout (green background, ✨ icon)
- Image (with caption)
- Video embed (YouTube, Loom)
- File attachment
- KB article link (inline embed)
- AI-Generate: "✨ Generate from ticket #____" — pulls resolution steps from a resolved ticket

**Auto-save**: Every 30 seconds + on every blur event. A subtle "Saved" indicator (12px, `--text-muted`) appears in the header and fades after 2 seconds.

**Version history**: Every save creates a version. Versions are accessible from the article header. A side-by-side diff view shows what changed between versions.

### 6.5 Semantic Search Experience

Searching from within the KB while editing a ticket (surfaced in the AI context panel):

**Inline KB search** in the reply composer: Typing `/kb` opens a floating search popover:
```
┌───────────────────────────────────────────────┐
│ 🔍 Search knowledge base...                   │
├───────────────────────────────────────────────┤
│ Relevant to this ticket:                       │
│ ⭐ VPN Setup Guide — 94% relevant              │
│ ⭐ VPN Troubleshooting — 89% relevant          │
│ ─────────────────────────────────────────────  │
│ [type to search all articles]                  │
└───────────────────────────────────────────────┘
```

Selecting an article inserts a link card inline in the reply — the reporter sees a nicely formatted KB article reference with title, excerpt, and link.

---

## 7. Mobile & Responsive UX

### 7.1 Mobile-First Adaptation Strategy

The mobile experience is not a "mobile version" — it is a **task-optimized variant** of the desktop experience. Mobile users perform a different subset of tasks: checking ticket status, adding quick comments, approving requests, and responding to escalations. The mobile UI is optimized for these flows specifically.

### 7.2 Mobile Layout System

**Breakpoints**:
```
xs: < 640px   — Mobile (primary mobile design)
sm: 640–768px — Large mobile / small tablet
md: 768–1024px — Tablet  
lg: 1024–1280px — Small desktop
xl: 1280px+   — Full desktop (all three panels)
```

**Mobile navigation** (< 768px):
The sidebar is replaced by a bottom navigation bar (56px height, `position: fixed, bottom: 0`). Five tabs: Home, Tickets, Search, Notifications, Menu.

The "Menu" tab opens a full-screen slide-up sheet (the nav items that don't fit in 5 tabs). The sheet has a 32px drag handle at the top — both click and swipe gesture to dismiss.

**Mobile ticket list**: Each ticket item is a card (not a row). Card layout:
```
┌─────────────────────────────────────────────────┐
│ [🔴 URGENT]           TKT-1847        [12:34]   │
│ VPN access issue for Marketing team             │
│ IT / Network • Ali Ben Ali           [SLA: 1h]  │
└─────────────────────────────────────────────────┘
```

**Swipe actions**: Left-swipe on a ticket card reveals: [Quick Reply] [Change Status] actions in a red/blue row. Right-swipe reveals: [Mark Resolved] (green). These swipe actions are discovered via a brief tutorial on first use (a swipe gesture indicator animates once on the first ticket).

### 7.3 Tablet Layout (768px – 1024px)

Two-panel layout: Navigation sidebar (collapsed, 48px) + Content area. The right context panel is hidden by default; opening a ticket shows the detail in a bottom sheet that occupies 70% of the viewport (the ticket list remains partially visible above).

This layout enables the "agent at the desk with a tablet" use case — monitoring the queue while having occasional detail views.

### 7.4 Mobile Quick Actions

A floating action button (FAB) at the bottom-right (`position: fixed`, 56px × 56px, `--cosmitto-red` background, white `+` icon). On tap: expands into a radial menu with 4 actions:
- 🎫 New Ticket
- 💬 Quick Comment
- 📞 Log Call
- 📎 Add Attachment

The radial expansion animation: actions fan out in a 120° arc (upper-left quadrant) over 200ms with spring easing.

### 7.5 Mobile AI Assistant

On mobile, the AI Copilot is accessible via a dedicated button in the ticket detail view (a ✨ icon in the comment composer toolbar). Tapping it opens a bottom sheet with:
- The AI draft (if available) — accepts scroll to read
- "Insert draft" button
- "Regenerate" option
- "Why did AI write this?" toggle

The mobile AI experience is intentionally simplified — no complex interaction, just the core value: a pre-written response ready to send.

### 7.6 Push Notification UX

Push notifications follow a hierarchy:

**Critical** (immediate, bypasses silent mode in user settings): SLA breach occurring NOW, ticket assigned to you, direct @mention
**Standard** (bundled in groups): New comment on your tickets, status changes
**Low** (batched, max 1/hour): AI insights, coaching tips, weekly digest

**Notification deep links**: Every push notification links directly to the relevant entity — tapping "New comment on TKT-1847" opens the mobile app directly to that ticket's thread, scrolled to the new comment (highlighted briefly with a yellow flash).

---

## 8. Accessibility & Performance UX

### 8.1 WCAG 2.1 AA Compliance — Specific Requirements

**Color contrast**: All body text meets 4.5:1 contrast ratio. Large text (18px+ regular or 14px+ bold) meets 3:1. Tested with automated tools (axe-core in CI pipeline) AND manual review.

**Color independence**: No information is conveyed by color alone. Status changes use color + icon + label. Priority uses color + icon + text label. SLA urgency uses color + countdown timer.

**Focus management**: Modal open → focus moves to first interactive element. Modal close → focus returns to the trigger element. No focus traps outside of modals and slide-overs.

**Keyboard navigation**: Every interactive element reachable by Tab. Tab order follows visual reading order (top-to-bottom, left-to-right). No "keyboard trap" — Esc always exits the current context.

**Skip links**: "Skip to main content" link as the first focusable element on every page (visible only on focus).

**ARIA implementation**:
- `role="dialog"` with `aria-labelledby` and `aria-describedby` on all modals
- `aria-live="polite"` on notification count badges (so screen readers announce count changes)
- `aria-expanded` on all collapsible elements
- `aria-current="page"` on active navigation items
- `role="status"` on all status update messages (toast notifications, inline confirmations)

### 8.2 Reduced Motion Support

```css
@media (prefers-reduced-motion: reduce) {
  /* Eliminate all animation */
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
  
  /* Exception: essential state change indicators */
  .status-badge-transition { transition-duration: 150ms !important; }
}
```

**Reduced motion alternatives**: Animations that communicate important state changes (e.g., notification arrival, AI generation) are replaced by instant visual state changes rather than being simply removed.

### 8.3 Optimistic UI — The Instant Feel

Every action the user takes should immediately reflect in the UI, before the server confirms it.

**Implementation pattern for all state changes**:
1. User clicks "Mark Resolved"
2. **Immediately** (0ms): Ticket status updates in UI, SLA timer stops, ticket row gets resolved styling, count badges update
3. API call is made in background
4. If success (< 2s typically): no change — the UI was already correct
5. If failure: revert all changes with an error toast: "Failed to resolve TKT-1847 · [Retry] [Undo]"

**Optimistic insert** (new comments): When an agent sends a reply, the comment appears in the thread immediately with a subtle "sending..." indicator (dots animation on the timestamp). If the send fails, the comment shows a red error state with "Send failed · [Retry] [Delete draft]".

**Conflict resolution**: If two agents both edit the same field simultaneously, the last save wins, but the other agent sees a toast: "This ticket was updated by Sara while you were editing. [Review changes]".

### 8.4 Virtualized Lists

Every list in the application with > 100 items uses virtual scrolling:
- Ticket queue (potentially 10,000+ tickets)
- Notification center
- Audit history
- User management table
- Knowledge base article list

**Implementation**: `react-virtual` or equivalent. Renders only visible items + 5 items above/below the fold (overscan). Scroll position is preserved on navigation (returning to the queue restores the exact scroll position).

**Scroll performance**: Target 60fps scrolling. Achieved by:
- No layout recalculation during scroll (all dimensions pre-calculated)
- Avatar images loaded as `loading="lazy"` with explicit `width`/`height`
- No `box-shadow` on individual list item rows (only on cards in grid views)
- Sticky headers via `position: sticky` (not JS-based)

### 8.5 Skeleton Loader Specificity

Every content area has a specific skeleton, not a generic block:

**Ticket list skeleton**:
```
[●●] [████████████] [██████████████████████████████] [█████] [██]
[●●] [████████████] [████████████████████████]       [█████] [██]
[●●] [████████████] [██████████████████████████████] [█████] [██]
```
(Priority dot, ID, title at varying lengths, status, age)

**KPI card skeleton**:
```
┌──────────────────────────────┐
│  [██████████████]            │
│                              │
│  [█████]                     │
│  [███████████████]           │
│                              │
│  [████████]                  │
└──────────────────────────────┘
```

The shimmer animation runs simultaneously across all skeletons on a page (synchronized by using `background-position` animation with shared timing).

### 8.6 Error UX — Recovery-First Design

**Form validation**:
- Validation fires on `blur` (not `keyup`) — avoids the "red box before I'm done typing" problem
- Required field errors show inline below the field, never as toast notifications
- Multi-field errors show one at a time (focus moves to first error)
- Successful validation: green checkmark for 1 second, then disappears (doesn't clutter the form)

**API errors**:
- 400-level errors: User-actionable message in a red callout within the form, not a modal
- 500-level errors: "Something went wrong — our team has been notified." with a Retry button. Never expose technical details to end users.
- Network errors: A top-banner: "Connection lost — working offline. Changes will sync when reconnected." with a connection status indicator.

**Empty states** (every possible empty state has a design):
- No tickets in queue: illustration (abstract, not clip-art) + "Your queue is empty · Nice work!" + "Create a ticket" CTA
- No search results: "No results for 'vpnn'" with a suggestion: "Did you mean 'vpn'?" + "Show all tickets" link
- No agents in a department: "No agents assigned · Add agents to this department" with direct action button
- First login (no data): A guided onboarding experience (see §9.4)

---

## 9. Enterprise Productivity Features

### 9.1 The Command Center — Power User Interface

For agents and managers who live in CosmittoHUB 8+ hours a day:

**Command center mode**: Activated by `⌘⇧K` (extended command palette). This is distinct from the standard `⌘K` palette — it includes system commands, admin actions, and developer-grade utilities:
```
ADMIN COMMANDS
  > flush-cache      — Refresh all data caches
  > export-queue     — Export current queue to CSV
  > broadcast-notice — Send notice to all active agents

DEVELOPER
  > copy-api-url ticket/1847  — Copy REST API URL
  > open-api-explorer         — Open Swagger UI
  > view-webhook-log          — Last 50 webhook deliveries
```

### 9.2 Keyboard-First Workflow System

**Full keyboard shortcut reference** (accessible via `?` key from any non-input context):

```
NAVIGATION
  g then d    → Dashboard
  g then q    → Queue
  g then m    → My tickets
  g then k    → Knowledge base
  g then r    → Reports
  g then s    → Settings

TICKET ACTIONS (when ticket is focused/open)
  e           → Edit title inline
  a           → Assign to agent
  s           → Change status
  p           → Change priority
  l           → Add label/tag
  m           → Apply macro
  c           → Add comment
  n           → Add internal note
  d           → Download attachments
  x           → Toggle selection (bulk mode)
  y           → Resolve ticket
  /           → Find in thread

GLOBAL
  ⌘K          → Command palette
  ⌘N          → New ticket
  ⌘⇧N        → New KB article
  ⌘.          → Toggle sidebar
  ⌘⇧L        → Toggle light/dark theme
  ?           → Keyboard shortcut help
  Esc         → Close panel / cancel / go back

QUEUE NAVIGATION
  j or ↓      → Next ticket
  k or ↑      → Previous ticket
  Enter       → Open selected ticket
  Space       → Preview ticket (keep queue focus)
  f           → Filter queue
  z           → Undo last action
```

**Chord navigation** (two-key sequences): The `g` then `[key]` pattern for navigation (borrowed from vim/Linear) allows 26 possible navigation destinations with just two keys. First press of `g` starts a 1-second window during which the second key is captured. Unrecognized chords are ignored (no error state).

**Action hints**: Every toolbar button shows its keyboard shortcut in the tooltip (e.g., hovering the "Assign" button shows "Assign (A)"). This teaches shortcuts passively through normal use.

### 9.3 Macro System — One-Click Workflows

**Macro library** (accessible via `⌘⇧M` or `M` in ticket context):

A searchable, categorized list of macros. Each macro shows:
- Name, description
- Actions it will perform (a compact action list)
- Last used date + usage count
- An AI recommendation score for the current ticket

**Creating a macro**:
Record mode — a "Record macro" button starts recording the agent's next sequence of actions as a macro. When recording is active, a subtle red recording indicator appears in the toolbar. Stopping recording opens a name/save dialog.

**Macro application confirmation** (for macros that change status or send messages): A 2-second preview before execution — showing exactly what will change. The preview is dismissible to allow fast application once users trust a macro.

### 9.4 Onboarding Experience — First Impression is Everything

**First login (new org)**:

Not a slideshow tour. An interactive setup wizard with four steps, each with a concrete action:

**Step 1 — "Set up your workspace"** (2 minutes):
- Upload logo (drag-drop zone, live preview)
- Set organization name
- Set timezone
- Choose primary language

**Step 2 — "Create your first department"** (3 minutes):
A guided department creation flow with a template picker: IT Support, HR, Facilities, Customer Success. Selecting a template pre-populates categories, SLA policies, and a default workflow. Users can edit or accept.

**Step 3 — "Invite your team"** (2 minutes):
A text area for email addresses (one per line or comma-separated). Each valid email gets a role selector (Agent/Manager/User) defaulting to Agent. Sending invites sends beautifully designed invitation emails.

**Step 4 — "Create your first ticket"** (2 minutes):
A prompted ticket creation flow with helper text on each field explaining what each field does. After creation, a celebration animation plays and the dashboard appears with the ticket visible.

**Progress**: Throughout the wizard, a progress bar (4 steps, circles) is always visible. Each completed step gets a checkmark + brief summary. The wizard can be exited at any step ("Skip setup — I'll configure later"), with a "Complete your setup" banner persisting in the dashboard until all steps are done.

**New agent onboarding** (joining an existing org):
Different flow — focuses on finding your queue, understanding your assigned tickets, and accessing the KB. A contextual tooltip system (coachmarks) highlights key UI elements on first encounter.

### 9.5 Workspace Presets — Saved Environments

Power users can save their entire workspace state as a preset:
- Current view (queue/board/timeline)
- Active filters
- Visible columns
- Sort order
- Open panels (right context panel open/closed)

Presets are saved to user profile and accessible from the nav or via `⌘⇧P`. Example presets a senior agent might have:
- "Morning triage" — All tickets, sorted by SLA urgency, no filters
- "My escalations" — My tickets, status = in_progress, priority >= high
- "End-of-day review" — All resolved today, CSAT not yet submitted

### 9.6 Activity Intelligence Feed

A persistent feed of relevant organizational activity, accessible from the sidebar and as a widget on the dashboard.

**Feed design**: Similar to GitHub's activity feed — compact, dense, scannable. Each item: avatar (24px) + past-tense action + entity link + timestamp.

```
👤 Sara resolved TKT-1843 · Printer offline, Floor 3                    2m ago
👤 Ahmed escalated TKT-1831 · VPN timeout to Level 2                   5m ago  
🤖 AI merged TKT-1847 + TKT-1849 · Identified as duplicate            12m ago
👤 Sonia created TKT-1850 · New employee laptop request               15m ago
✅  TKT-1798 auto-closed · No response after 72h (per policy)         18m ago
📊  SLA compliance reached 94.5% · Target achieved for first time     1h ago
```

**Feed filtering**: Users can configure which activity types appear in their feed. They can follow specific agents (their activity is highlighted with an outline), departments, or ticket categories.

---

## 10. Complete Design System

### 10.1 Typography Scale — Complete Specification

```css
/* Display — Staatliches (Cosmitto brand, data/numbers) */
.text-display-2xl { font: 700 72px/1.0 'Staatliches'; letter-spacing: -1px; }
.text-display-xl  { font: 700 56px/1.0 'Staatliches'; letter-spacing: -0.5px; }
.text-display-lg  { font: 700 40px/1.1 'Staatliches'; letter-spacing: -0.25px; }
.text-display-md  { font: 700 32px/1.1 'Staatliches'; }
.text-display-sm  { font: 700 24px/1.2 'Staatliches'; }

/* Interface — IBM Plex Sans (all UI text) */
.text-2xl  { font: 600 20px/1.3 'IBM Plex Sans'; }
.text-xl   { font: 600 18px/1.3 'IBM Plex Sans'; }
.text-lg   { font: 500 16px/1.4 'IBM Plex Sans'; }
.text-base { font: 400 14px/1.5 'IBM Plex Sans'; }
.text-sm   { font: 400 13px/1.5 'IBM Plex Sans'; }
.text-xs   { font: 400 12px/1.4 'IBM Plex Sans'; }
.text-2xs  { font: 400 11px/1.4 'IBM Plex Sans'; }

/* Mono — IBM Plex Mono (IDs, code, numbers) */
.text-mono-sm  { font: 400 13px/1.4 'IBM Plex Mono'; }
.text-mono-xs  { font: 400 12px/1.4 'IBM Plex Mono'; }
```

### 10.2 Complete Color Token System

```css
:root {
  /* Brand */
  --color-brand:          #DC2626;
  --color-brand-hover:    #B91C1C;
  --color-brand-light:    rgba(220, 38, 38, 0.1);
  --color-brand-subtle:   rgba(220, 38, 38, 0.06);

  /* Surfaces (dark mode — primary) */
  --surface-base:         #080B10;
  --surface-1:            #0F172A;
  --surface-2:            #1E293B;
  --surface-3:            #263245;
  --surface-4:            #334155;
  --surface-5:            #475569;

  /* Text */
  --text-primary:         #F8FAFC;
  --text-secondary:       #CBD5E1;
  --text-muted:           #94A3B8;
  --text-faint:           #64748B;
  --text-disabled:        #475569;
  --text-inverse:         #080B10;

  /* Borders */
  --border-subtle:        rgba(255,255,255,0.06);
  --border-default:       rgba(255,255,255,0.10);
  --border-strong:        rgba(255,255,255,0.16);
  --border-focus:         #6366F1;

  /* Status semantic */
  --status-new:           #6366F1;
  --status-new-bg:        rgba(99, 102, 241, 0.12);
  --status-progress:      #0EA5E9;
  --status-progress-bg:   rgba(14, 165, 233, 0.12);
  --status-waiting:       #F59E0B;
  --status-waiting-bg:    rgba(245, 158, 11, 0.12);
  --status-resolved:      #10B981;
  --status-resolved-bg:   rgba(16, 185, 129, 0.12);
  --status-closed:        #64748B;
  --status-closed-bg:     rgba(100, 116, 139, 0.12);
  --status-cancelled:     #EF4444;
  --status-cancelled-bg:  rgba(239, 68, 68, 0.12);

  /* Priority semantic */
  --priority-critical:    #DC2626;
  --priority-urgent:      #F97316;
  --priority-high:        #F59E0B;
  --priority-medium:      #3B82F6;
  --priority-low:         #64748B;

  /* AI semantic */
  --ai-primary:           #8B5CF6;
  --ai-bg:                rgba(139, 92, 246, 0.10);
  --ai-border:            rgba(139, 92, 246, 0.25);
  --ai-text:              #C4B5FD;

  /* Feedback */
  --success:              #10B981;
  --success-bg:           rgba(16, 185, 129, 0.10);
  --warning:              #F59E0B;
  --warning-bg:           rgba(245, 158, 11, 0.10);
  --error:                #EF4444;
  --error-bg:             rgba(239, 68, 68, 0.10);
  --info:                 #0EA5E9;
  --info-bg:              rgba(14, 165, 233, 0.10);
}

/* Light mode overrides */
[data-theme="light"] {
  --surface-base:         #F8FAFC;
  --surface-1:            #FFFFFF;
  --surface-2:            #F1F5F9;
  --surface-3:            #E2E8F0;
  --surface-4:            #CBD5E1;
  --surface-5:            #94A3B8;
  --text-primary:         #0F172A;
  --text-secondary:       #334155;
  --text-muted:           #64748B;
  --text-faint:           #94A3B8;
  --border-subtle:        rgba(0,0,0,0.05);
  --border-default:       rgba(0,0,0,0.09);
  --border-strong:        rgba(0,0,0,0.14);
}
```

### 10.3 Button Component System

**Seven button variants**:

```
PRIMARY      [bg: --color-brand,        text: white]
SECONDARY    [bg: --surface-3,          text: --text-primary,   border: --border-default]
GHOST        [bg: transparent,          text: --text-secondary,  hover-bg: --surface-3]
DANGER       [bg: #EF4444,              text: white]
DANGER GHOST [bg: transparent,          text: #EF4444,           hover-bg: rgba(239,68,68,0.08)]
AI           [bg: --ai-bg,              text: --ai-text,         border: --ai-border]
LINK         [bg: transparent,          text: --color-brand,     underline on hover]
```

**Three button sizes**:
```
LG:  height 40px, padding 0 20px, font-size 14px/600, border-radius 8px
MD:  height 32px, padding 0 14px, font-size 13px/500, border-radius 6px
SM:  height 28px, padding 0 10px, font-size 12px/500, border-radius 5px
```

**Button states** (all variants):
- Default → Hover (background lightens/darkens 8%) → Active (background deepens 12%, scale 0.98) → Disabled (opacity 0.4, cursor not-allowed) → Loading (spinner replaces or prepends icon, text shifts)

**Loading state**: A 14px spinner appears inside the button with a 40ms delay (prevents spinner flash for fast responses). Button width does not change during loading.

**Icon buttons** (square, icon only): Same variants, same heights, equal width (40px/32px/28px). Tooltip required on all icon-only buttons.

### 10.4 Form Component System

**Input field**:
```css
.input {
  height: 36px;
  padding: 0 12px;
  background: var(--surface-1);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font: 400 14px/1 'IBM Plex Sans';
  color: var(--text-primary);
  transition: border-color 150ms, box-shadow 150ms;
}
.input:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
  outline: none;
}
.input::placeholder { color: var(--text-faint); }
.input.error { border-color: var(--error); }
.input.error:focus { box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.15); }
```

**Field anatomy** (full form field):
```
[Label (12px/500, --text-secondary, 6px bottom margin)]
[Optional help text below label (12px, --text-muted)]
[Input]
[Error message OR success message (12px, appears below input)]
```

**Select** (custom, not native `<select>`): Same dimensions as input. The dropdown opens as a popover below the trigger — not `<option>` elements. Dropdown items: 36px height, same hover as nav items. Searchable when > 10 options (search input auto-focuses in the dropdown).

**Checkbox**: 16px × 16px. Default: `--surface-3` background, `--border-default` border, `--radius-sm`. Checked: `--color-brand` background, checkmark SVG in white. Indeterminate: horizontal dash in `--color-brand`. Focus ring: `--border-focus` with 3px shadow.

**Toggle switch**: 36px × 20px track, 16px circle thumb. Off: `--surface-4` track. On: `--color-brand` track. Transition: thumb slides in 150ms, track color transitions in 150ms. No border on thumb — clean design.

### 10.5 Badge & Status Component System

**Status badge**:
```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 22px;
  padding: 0 8px;
  border-radius: var(--radius-sm);
  font: 500 11px/1 'IBM Plex Sans';
  text-transform: uppercase;
  letter-spacing: 0.4px;
}
.badge-new        { background: var(--status-new-bg);       color: var(--status-new); }
.badge-progress   { background: var(--status-progress-bg);  color: var(--status-progress); }
.badge-waiting    { background: var(--status-waiting-bg);   color: var(--status-waiting); }
.badge-resolved   { background: var(--status-resolved-bg);  color: var(--status-resolved); }
.badge-closed     { background: var(--status-closed-bg);    color: var(--status-closed); }
.badge-cancelled  { background: var(--status-cancelled-bg); color: var(--status-cancelled); }
```

**Priority indicator** (dot only, for table views):
```css
.priority-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.priority-critical { background: var(--priority-critical); box-shadow: 0 0 6px var(--priority-critical); }
.priority-urgent   { background: var(--priority-urgent); }
.priority-high     { background: var(--priority-high); }
.priority-medium   { background: var(--priority-medium); }
.priority-low      { background: var(--priority-low); }
```

### 10.6 Data Table Component

The data table is the most complex component in the system. Requirements:

**Features**:
- Virtualized rendering (only visible rows rendered)
- Sortable columns (click header, cycles asc/desc/none)
- Resizable columns (drag handle on header borders, 4px wide, appears on hover)
- Reorderable columns (drag header to reorder)
- Pinned columns (left: fixed columns; right: action column)
- Row selection (checkbox column, optional)
- Expandable rows (click to reveal sub-table)
- Empty state slot (custom content when no rows)
- Pagination or infinite scroll mode
- Column visibility control (show/hide via popover)

**Row height variants**: Compact (32px), Standard (40px), Comfortable (52px)

**Header design**:
```css
.table-header-cell {
  height: 36px;
  padding: 0 12px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border-default);
  font: 500 12px/1 'IBM Plex Sans';
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  user-select: none;
  cursor: pointer;
}
.table-header-cell:hover { color: var(--text-primary); }
.table-header-cell.sorted { color: var(--text-primary); }
```

### 10.7 Modal & Dialog System

**Base modal**:
- Max-widths: SM (400px), MD (560px), LG (720px), XL (960px), Full (90vw)
- Opens: overlay fades in 150ms + dialog scales from `scale(0.96)` to `scale(1)` in 200ms
- Closes: reverse animation in 150ms
- Overlay: `rgba(0,0,0,0.6)` with `backdrop-filter: blur(4px)`
- Focus trap: Tab cycles only within modal content
- Esc to close (if closeable)

**Slide-over panel** (right-side):
- Widths: SM (360px), MD (480px), LG (600px)
- Slides in from right: `translateX(100%) → translateX(0)` in 250ms
- Overlay: `rgba(0,0,0,0.4)` (lighter than modal — panel is less disruptive)
- Does not block main content interaction (unless explicitly modal)

**Confirmation dialog** (destructive actions only):
```
┌────────────────────────────────────────┐
│  Delete department "IT Network"?       │
│                                        │
│  This will remove 12 agents from the  │
│  department. They won't lose access   │
│  to their tickets.                    │
│                                        │
│  [Cancel]              [Delete dept]  │
└────────────────────────────────────────┘
```
The destructive button is always on the RIGHT (industry standard for destructive confirmations). The "Delete" button is red/danger variant. "Cancel" is secondary.

### 10.8 Toast Notification System

**Toast anatomy** (320px wide):
```
┌──────────────────────────────────────────────┐
│  [✓ icon]  TKT-1847 marked as resolved       │
│            [Undo ↩]              [×]         │
└──────────────────────────────────────────────┘
```

**Toast variants**: Success (green left border, ✓ icon), Error (red left border, ✗ icon), Warning (amber left border, ⚠ icon), Info (blue left border, ℹ icon)

**Toast with action**: "Undo" links for reversible actions (appears for 4 seconds, then auto-dismisses with the toast). Clicking "Undo" reverses the optimistic UI change and shows a "Reversed" toast.

**Toast stacking**: Up to 3 toasts visible. Position: `position: fixed; bottom: 24px; right: 24px`. New toasts push older ones up with spring animation.

### 10.9 AI Component Variants

**AI Suggestion chip** (inline, in ticket fields):
```css
.ai-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: var(--ai-bg);
  border: 1px solid var(--ai-border);
  border-radius: var(--radius-full);
  font: 500 11px/1 'IBM Plex Sans';
  color: var(--ai-text);
  cursor: pointer;
}
.ai-chip::before { content: '✨ '; }
```

**AI insight card** (in context panels):
```css
.ai-card {
  background: linear-gradient(
    135deg,
    rgba(139, 92, 246, 0.08) 0%,
    rgba(99, 102, 241, 0.06) 100%
  );
  border: 1px solid var(--ai-border);
  border-radius: var(--radius-lg);
  padding: 16px;
}
```

**AI loading state** (during generation):
A distinctive animation: three dots (`···`) with staggered fade-pulse (each dot cycles opacity 1→0.3→1 with 200ms offset). This is distinct from the standard spinner and signals "AI is thinking" specifically.

### 10.10 Empty State Design Language

Every empty state follows a consistent structure:

```
[Illustration — 80×80px SVG, abstract/geometric, brand colors]
[Heading — 18px/600, --text-primary]
[Description — 14px/400, --text-muted, max 2 lines]
[Primary CTA button]
[Secondary link (optional)]
```

**Illustration style**: Abstract geometric compositions (not character illustrations, not generic icons). Composed from circles, triangles, and lines in brand colors with low opacity. They suggest the concept without being literal — e.g., the empty queue illustration is an abstract balance scale composed of dots and lines, suggesting "equilibrium."

### 10.11 Animation Principles — Complete Specification

```css
/* Timing functions */
--ease-default:   cubic-bezier(0.4, 0, 0.2, 1);   /* Material standard */
--ease-in:        cubic-bezier(0.4, 0, 1, 1);       /* Accelerate */
--ease-out:       cubic-bezier(0, 0, 0.2, 1);       /* Decelerate */
--ease-spring:    cubic-bezier(0.34, 1.56, 0.64, 1); /* Overshoot */
--ease-linear:    linear;

/* Duration scale */
--duration-instant:  0ms;     /* Immediate feedback */
--duration-fast:     100ms;   /* Hover states */
--duration-default:  150ms;   /* Most transitions */
--duration-moderate: 200ms;   /* Entrance animations */
--duration-slow:     300ms;   /* Complex animations */
--duration-deliberate: 400ms; /* Status changes, celebrations */
```

**Animation rules table**:

| Animation type | Duration | Easing | Notes |
|---|---|---|---|
| Hover background | 100ms | --ease-default | Never animate other properties on hover |
| Focus ring appear | 150ms | --ease-out | |
| Tooltip appear | 150ms | --ease-out | Delay: 400ms |
| Tooltip disappear | 100ms | --ease-in | No delay |
| Modal open | 200ms | --ease-out | Scale + fade |
| Modal close | 150ms | --ease-in | Faster close than open |
| Slide-over open | 250ms | --ease-spring | Slight overshoot |
| Toast appear | 200ms | --ease-spring | Slide up from bottom |
| Toast dismiss | 150ms | --ease-in | Slide right + fade |
| Status badge change | 400ms | --ease-spring | Shrink + color + expand |
| Drag pick up | 200ms | --ease-out | Scale + shadow |
| Drag drop | 300ms | --ease-spring | Spring into position |
| Page transition | 150ms | --ease-default | Fade only (no slide on desktop) |
| Command palette open | 200ms | --ease-spring | Scale + fade |
| Skeleton shimmer | 1500ms | --ease-linear | Infinite loop |
| AI typewriter | Variable | Linear | ~400 chars/second |

---

*This document represents the complete UX/UI enhancement specification for CosmittoHUB.*  
*Implementation should proceed section by section, with Phase 0 prioritizing §2 (Global UI) and §3 (Ticket Management) as the highest-impact surfaces.*

*Design tokens (§10.2) and typography (§10.1) should be implemented before any component work begins — they are the foundation everything else is built on.*
