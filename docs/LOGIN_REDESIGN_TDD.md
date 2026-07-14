# Secure Examination System — Login Page Redesign

## Technical Design Document & Implementation Guide

**Author:** Senior UI/UX Designer / Frontend Engineer
**Status:** Design Spec v1.0
**Target stack (current):** Django templates · Tailwind CSS (CDN) · Lucide icons
**Recommended target stack:** React + Vite · Tailwind CSS · Framer Motion · Lucide-React

---

## 0. Context: What We Are Replacing

The current `exam_system/templates/login.html` is the well-known "sign-in / sign-up"
sliding-overlay template:

- Two `<form>` blocks sit side-by-side (`student-container`, `instructor-container`)
  inside a `768px` white `.container`.
- A blue `.overlay` slides left/right via `.right-panel-active` on `container`.
- Role selection is hidden behind *"Sign In as Student / Instructor"* ghost buttons
  that trigger a 0.6s transform animation.

**Why this fails the brief:** it is the textbook "template-looking sliding panel,"
it hides the form behind a marketing overlay until you click, and it offers no
perception of layered depth or product credibility (no feature list, no brand
anchor). The redesign moves to a **single centered glass card with an in-card
tabbed role selector** plus (optional) a **feature panel** for the two-column hero.

---

## 1. Visual Design Specification — Layered Background

The background is a **stacked z-index composition**, not a single gradient. Each
layer is a dedicated element so it can be animated, themed, and removed
independently. Bottom → top:

| Z | Layer | Purpose | Key properties |
|---|-------|---------|----------------|
| 0 | `BgGradient` | Flat, near-white base so content never floats on pure white | `background: linear-gradient(160deg,#f8fafc 0%, #eef2f7 100%)` |
| 1 | `BlurredBlobs` | Soft depth + brand color bleed (the only "gradient" allowed, heavily blurred) | 2–3 absolutely-positioned `div`s, `filter: blur(90px)`, `opacity:.45`, `mix-blend-multiply` |
| 2 | `DotGrid` | Subtle "engineering/blueprint" texture conveying precision | `background-image: radial-gradient(#cbd5e1 1px, transparent 1px)`; `background-size: 22px 22px`; masked with radial fade |
| 3 | `DecorativeSVG` | Abstract shield/connection motif (security signal) | Hand-authored inline SVG, `opacity:.06`, pinned to corners |
| 4 | Foreground | `AuthCard` + copy (the only sharp, high-contrast layer) | — |

### 1.1 Layer CSS (reference values)

```css
/* Layer 0 — base */
.auth-bg {
  position: fixed; inset: 0; z-index: 0;
  background: linear-gradient(160deg, #f8fafc 0%, #eef2f7 60%, #e9eef6 100%);
}

/* Layer 1 — blurred brand blobs */
.auth-blob {
  position: fixed; border-radius: 9999px;
  filter: blur(90px); opacity: .45; mix-blend-mode: multiply;
  pointer-events: none; z-index: 1;
}
.auth-blob--blue   { width: 420px; height: 420px; top: -120px; left: -80px;
                     background: radial-gradient(circle, #3b82f6, transparent 70%); }
.auth-blob--indigo { width: 380px; height: 380px; bottom: -140px; right: -60px;
                     background: radial-gradient(circle, #6366f1, transparent 70%); }

/* Layer 2 — dot grid with radial fade mask */
.auth-dots {
  position: fixed; inset: 0; z-index: 2; pointer-events: none;
  background-image: radial-gradient(#cbd5e1 1px, transparent 1px);
  background-size: 22px 22px;
  -webkit-mask-image: radial-gradient(circle at 50% 40%, #000 0%, transparent 75%);
          mask-image: radial-gradient(circle at 50% 40%, #000 0%, transparent 75%);
}

/* Layer 3 — decorative SVG sits at z-index 3; card at z-index 10 */
```

**Animation for blobs (subtle, premium):** slow independent float, 18–24s,
`ease-in-out infinite alternate` on `transform: translate3d()` only (GPU-cheap).

---

## 2. Component Architecture

Reusable, framework-agnostic breakdown. Tree for the recommended React build, but
each maps 1:1 to a Django template partial / server-rendered block.

```
<AuthPage>                      // full-screen layout, owns background + grid
 ├─ <LayeredBackground>         // composes BgGradient + BlurredBlobs + DotGrid + DecorativeSVG
 ├─ <AuthShell>                 // two-column hero wrapper (marketing | card) or single centered
 │   ├─ <MarketingPanel>        // (optional) BrandHeader + FeatureList + trust signals
 │   │   ├─ <BrandHeader/>      // logo + product name
 │   │   └─ <FeatureList/>      // Lucide-check bullet list of security assurances
 │   └─ <AuthCard>              // glassmorphism surface
 │       ├─ <BrandHeader/>      // compact logo lockup (mobile / single-col)
 │       ├─ <RoleSelectorTabs>  // Student | Instructor — animated indicator (layoutId)
 │       ├─ <LoginForm role={active}>
 │       │   ├─ <InputWithIcon label icon type error/>
 │       │   │    × 2 (username, password)
 │       │   ├─ <PasswordToggle/>   // eye / eye-off (+ optional strength)
 │       │   └─ <SubmitButton/>     // primary CTA, loading state
 │       └─ <CardFooter/>           // "Secured by …" + admin-contact note
```

### Component contracts

| Component | Props / Slots | Responsibility |
|-----------|---------------|----------------|
| `LayeredBackground` | `variant: 'login' \| 'register'` | Renders z0–z3; blob positions vary per variant |
| `AuthCard` | `children` | Glass surface: `backdrop-filter`, border, shadow-lg→xl hover |
| `RoleSelectorTabs` | `value`, `onChange`, `options[]` | Controlled tab state; sliding pill via shared-layout |
| `InputWithIcon` | `label, icon, type, error, ...input` | Label, leading Lucide icon, focus ring, error border + message |
| `FeatureList` | `items[]` | Renders `Check` icon + label; staggered entrance |
| `SubmitButton` | `loading`, `children` | Disabled/loading spinner, hover lift, active press |

---

## 3. Detailed Styling Guide — Design System

### 3.1 Color tokens

```css
:root {
  --brand-600: #2563eb;   /* primary action */
  --brand-700: #1d4ed8;   /* hover        */
  --brand-500: #3b82f6;   /* blob / accent */
  --brand-100: #dbeafe;   /* tint bg      */
  --bg:       #f8fafc;    /* slate-50     */
  --surface:  #ffffff;
  --text:     #0f172a;    /* slate-900    */
  --text-mut: #64748b;    /* slate-500    */
  --border:   #e2e8f0;    /* slate-200    */
  --err:      #dc2626;    /* red-600      */
  --err-bg:   #fef2f2;
  --err-bd:   #fecaca;
  --ok:       #16a34a;
}
```

Use `rgba(37,99,235, …)` for focus rings and tinted shadows.

### 3.2 Typography scale (font: Inter, fallback system-ui)

| Token | Size | Weight | Line-height | Tracking | Usage |
|-------|------|--------|-------------|----------|-------|
| `display` | 30px / 1.875rem | 700 | 1.2 | -0.02em | Card title "Sign in" |
| `h2`      | 20px / 1.25rem  | 600 | 1.3 | -0.01em | Section / panel heads |
| `body`    | 15px / 0.9375rem| 400 | 1.6 | 0 | Inputs, paragraphs |
| `small`   | 13px / 0.8125rem| 500 | 1.5 | 0 | Labels, hints |
| `caption` | 12px / 0.75rem  | 400 | 1.4 | 0 | Footer, admin note |

### 3.3 Radius standards

```
--r-sm: 8px   /* inputs, tags        */
--r-md: 12px  /* buttons, pills      */
--r-lg: 16px  /* inner panels        */
--r-xl: 20px  /* AuthCard            */
--r-pill: 9999px
```

### 3.4 Shadow depths (the refined `box-shadow` logic)

Replace the old `0 14px 28px rgba(0,0,0,.25)` (too dark/harsh) with a
low-opacity, multi-layer system that reads as *lifted glass*, not a drop-shadow
sticker:

```css
--shadow-sm: 0 1px 2px rgba(15,23,42,.04), 0 1px 3px rgba(15,23,42,.06);
--shadow-md: 0 4px 6px -1px rgba(15,23,42,.05), 0 2px 4px -2px rgba(15,23,42,.05);
--shadow-lg: 0 10px 25px -3px rgba(15,23,42,.08), 0 4px 10px -4px rgba(15,23,42,.06); /* card rest */
--shadow-xl: 0 20px 40px -8px rgba(15,23,42,.12), 0 8px 16px -8px rgba(15,23,42,.08); /* card hover */
--ring-focus: 0 0 0 4px rgba(37,99,235,.14);
--glass-edge: inset 0 1px 0 rgba(255,255,255,.6);
```

### 3.5 Input field states

State is expressed by **border + ring + icon color**, never by heavy fills.

```css
.input {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  padding: 12px 14px 12px 42px;   /* left pad for leading icon */
  color: var(--text);
  transition: border-color .18s ease, box-shadow .18s ease, background .18s ease;
}
.input::placeholder { color: #94a3b8; }

.input:hover  { border-color: #cbd5e1; }

.input:focus  {                                 /* DEFAULT / FOCUS */
  background: var(--surface);
  border-color: var(--brand-600);
  box-shadow: var(--ring-focus);
  outline: none;
}

.input:disabled { opacity: .6; cursor: not-allowed; background: #f1f5f9; }

.input.is-error {                                /* ERROR */
  border-color: var(--err);
  box-shadow: 0 0 0 4px rgba(220,38,38,.12);
  background: var(--err-bg);
}
.input.is-error + .input-msg { color: var(--err); }   /* helper/error text */
```

Leading icon: `position:absolute; left:14px; top:50%; translateY(-50%); color:#94a3b8`;
on focus/error, icon color follows (`#2563eb` / `#dc2626`) via `:focus-within`.

---

## 4. Interaction & Animation Logic

Goal: **premium = restraint.** No 0.6s panel slides. Use short, eased,
transform/opacity-only motion (GPU), with a shared-layout tab indicator.

### 4.1 Card entrance (mount)

- `opacity 0 → 1`, `translateY(16px) → 0`, `scale(.98) → 1`.
- Duration **450ms**, `cubic-bezier(.22,1,.36,1)` (easeOutExpo-ish).
- Stagger children (header → tabs → fields → button) by **60ms**.
- Respect `prefers-reduced-motion`: collapse to a simple fade.

### 4.2 Tab switching (RoleSelectorTabs)

- Active pill/underline uses **shared-layout animation** (`layoutId` in Framer
  Motion / `::view-transition` or a transitioned transform in vanilla).
- Switching content uses `AnimatePresence mode="wait"`: outgoing fades+shifts
  `x:-8, opacity:0` (120ms), incoming fades+shifts `x:8→0, opacity:0→1` (180ms).
- This gives a clean **fade/transform**, not a panel slide.

### 4.3 Micro-interactions

| Element | Motion |
|---------|--------|
| `SubmitButton` hover | `translateY(-1px)` + shadow-md→lg |
| `SubmitButton` active | `translateY(0) scale(.98)` |
| `InputWithIcon` focus | ring grows (box-shadow transition), icon tints brand |
| `PasswordToggle` | icon cross-fade eye ↔ eye-off |
| Background blobs | independent 18–24s float (see §1) |
| FeatureList items | staggered `y:8→0, opacity:0→1` on mount |

### 4.4 Framer Motion snippets (recommended stack)

```tsx
// Card entrance
<motion.div
  initial={{ opacity: 0, y: 16, scale: 0.98 }}
  animate={{ opacity: 1, y: 0, scale: 1 }}
  transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
>

// Tab content swap
<AnimatePresence mode="wait">
  <motion.div
    key={role}
    initial={{ opacity: 0, x: 8 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: -8 }}
    transition={{ duration: 0.18, ease: "easeOut" }}
  >
    <LoginForm role={role} />
  </motion.div>
</AnimatePresence>

// Sliding tab indicator
{options.map(o => (
  <button key={o.id} onClick={() => setRole(o.id)}>
    {o.label}
    {role === o.id && (
      <motion.span layoutId="tab-pill" className="tab-pill" />
    )}
  </button>
))}
```

---

## 5. Frontend Implementation Plan

### 5.1 Recommended path (target state)

```
exam_system/
 ├─ frontend/                 # Vite + React app
 │   ├─ src/
 │   │   ├─ components/auth/{AuthPage,LayeredBackground,AuthCard,
 │   │   │                    RoleSelectorTabs,InputWithIcon,FeatureList,
 │   │   │                    SubmitButton}.tsx
 │   │   ├─ styles/tokens.css # §3 design tokens
 │   │   └─ main.tsx
 │   └─ tailwind.config.js    # brand colors + radius + shadow extensions
 └─ views.py                  # render auth SPA shell; keep DRF/JWT login API
```

- **Tailwind** carries the tokens: extend `theme.colors.brand`, `borderRadius`,
  `boxShadow`, and use `backdrop-blur` utilities for glass.
- **Framer Motion** for §4 animations.
- Django keeps owning auth (session or `djangorestframework-jwt`); the SPA calls
  the existing `login` endpoint with `role` + `username` + `password`.

### 5.2 Pragmatic MVP (no build — matches current stack)

Rewrite `login.html` in place using **Tailwind CDN + Lucide + ~40 lines of
vanilla JS** (no Vue/React toolchain). This ships today and follows the exact
same tokens. The three critical pieces:

#### (a) Layered background (Django template)

```html
<body class="min-h-screen overflow-hidden text-slate-900 antialiased">
  <!-- z0 base -->
  <div class="fixed inset-0 -z-10"
       style="background:linear-gradient(160deg,#f8fafc,#eef2f7 60%,#e9eef6)"></div>
  <!-- z1 blobs -->
  <div class="fixed -z-10 top-[-120px] left-[-80px] w-[420px] h-[420px] rounded-full blur-[90px] opacity-45 mix-blend-multiply"
       style="background:radial-gradient(circle,#3b82f6,transparent 70%);animation:float1 22s ease-in-out infinite alternate"></div>
  <div class="fixed -z-10 bottom-[-140px] right-[-60px] w-[380px] h-[380px] rounded-full blur-[90px] opacity-45 mix-blend-multiply"
       style="background:radial-gradient(circle,#6366f1,transparent 70%);animation:float2 24s ease-in-out infinite alternate"></div>
  <!-- z2 dot grid -->
  <div class="fixed inset-0 -z-10 pointer-events-none auth-dots"></div>

  <style>
    .auth-dots{background-image:radial-gradient(#cbd5e1 1px,transparent 1px);
      background-size:22px 22px;
      -webkit-mask-image:radial-gradient(circle at 50% 40%,#000,transparent 75%);
      mask-image:radial-gradient(circle at 50% 40%,#000,transparent 75%);}
    @keyframes float1{to{transform:translate3d(40px,30px,0)}}
    @keyframes float2{to{transform:translate3d(-30px,-40px,0)}}
  </style>
```

#### (b) Glassmorphism card + tabbed role selector

```html
<main class="relative z-10 min-h-screen grid place-items-center p-4">
  <div class="w-full max-w-md rounded-[20px] border border-white/60 p-8
              bg-white/70 backdrop-blur-xl backdrop-saturate-150
              shadow-[0_20px_40px_-8px_rgba(15,23,42,.12)]">
    <!-- brand -->
    <div class="flex items-center gap-2 mb-6">
      <i data-lucide="shield-check" class="w-6 h-6 text-brand-600"></i>
      <span class="text-lg font-semibold">Secure Examination System</span>
    </div>

    <!-- RoleSelectorTabs -->
    <div class="relative flex p-1 mb-6 rounded-xl bg-slate-100" role="tablist">
      <span id="tab-pill" class="absolute inset-y-1 left-1 w-[calc(50%-4px)]
            rounded-lg bg-white shadow-sm transition-transform duration-200"></span>
      <button data-role="student"    class="relative z-10 flex-1 py-2 text-sm font-medium">Student</button>
      <button data-role="instructor" class="relative z-10 flex-1 py-2 text-sm font-medium">Instructor</button>
    </div>

    <form method="post" action="{% url 'login' %}">
      {% csrf_token %}
      <input type="hidden" name="role" id="role-input" value="student">

      <label class="block text-sm font-medium mb-1">Username</label>
      <div class="relative mb-4">
        <i data-lucide="user" class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"></i>
        <input name="username" required autocomplete="username"
               class="w-full rounded-lg bg-slate-50 border border-slate-200
                      pl-10 pr-3 py-3 text-[15px] outline-none transition
                      focus:bg-white focus:border-brand-600 focus:ring-4 focus:ring-brand-600/15">
      </div>

      <label class="block text-sm font-medium mb-1">Password</label>
      <div class="relative mb-6">
        <i data-lucide="lock" class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"></i>
        <input type="password" name="password" id="pw" required autocomplete="current-password"
               class="w-full rounded-lg bg-slate-50 border border-slate-200
                      pl-10 pr-10 py-3 text-[15px] outline-none transition
                      focus:bg-white focus:border-brand-600 focus:ring-4 focus:ring-brand-600/15">
        <button type="button" onclick="togglePw()" class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
          <i data-lucide="eye" id="eye"></i>
        </button>
      </div>

      <button class="w-full flex items-center justify-center gap-2 rounded-xl py-3
                     font-semibold text-white bg-brand-600 shadow-md transition
                     hover:bg-brand-700 hover:-translate-y-px hover:shadow-lg active:scale-[.98]">
        <i data-lucide="log-in" class="w-4 h-4"></i> Sign In
      </button>
    </form>
  </div>
</main>

<script>
  const pill = document.getElementById('tab-pill');
  const roleInput = document.getElementById('role-input');
  document.querySelectorAll('[data-role]').forEach(btn => {
    btn.onclick = () => {
      const isStudent = btn.dataset.role === 'student';
      pill.style.transform = isStudent ? 'translateX(0)' : 'translateX(100%)';
      roleInput.value = btn.dataset.role;
    };
  });
  function togglePw(){ const p=document.getElementById('pw'),e=document.getElementById('eye');
    p.type = p.type==='password'?'text':'password';
    e.setAttribute('data-lucide', p.type==='password'?'eye':'eye-off'); lucide.createIcons(); }
  lucide.createIcons();
</script>
```

> Tailwind CDN note: `bg-brand-600` / `ring-brand-600/15` require the brand color
> registered via `tailwind.config` or an inline `tailwind.config = { theme: { extend:
> { colors: { brand: { 600:'#2563eb', 700:'#1d4ed8' } } } } }` script before the CDN,
> or simply use arbitrary values `bg-[#2563eb]`.

### 5.3 Build order

1. Tokens (`tokens.css` / Tailwind config) → 2. `LayeredBackground` → 3. `AuthCard` glass
→ 4. `RoleSelectorTabs` (indicator + state) → 5. `InputWithIcon` + states →
6. `FeatureList` + `MarketingPanel` (optional) → 7. Entrance/stagger + tab transition
→ 8. `prefers-reduced-motion` + responsive (single column < `md`) → 9. Wire Django
`login` view (`role` + validation + messages).

---

## 6. UX Refinement — Why This Reads as "Secure & Professional"

- **From hidden overlay → in-card tabs:** the old design forced users to *discover*
  the form behind a sliding panel; role choice was a secondary ghost button. Tabs
  put role selection **front-and-center and instantly reversible**, signaling a
  considered, configurable product rather than a generic auth widget. No motion
  gimmick = less "toy app," more "enterprise tool."
- **Layered depth (blur + dots + glass):** depth cues (foreground sharp, background
  soft) are a known trust signal — they imply a real, dimensional product surface,
  the visual language of Notion/Canvas/Stripe rather than a flat form.
- **Feature list / security assurances:** explicitly surfacing "encrypted sessions,
  proctoring, admin-provisioned accounts" answers the latent question *"is this safe
  to put my exam data into?"* before the user types a password — reducing anxiety
  and abandoned logins.
- **Restrained motion:** short eased transitions + focus rings communicate
  responsiveness and control (security = "the system reacts precisely to me"),
  while avoiding the disorienting 0.6s slides that feel unpolished.
- **High-quality iconography (Lucide):** consistent 24px stroke icons across brand,
  inputs, and features create cohesion that reads as "designed," not assembled.

---

## Appendix — Decision Summary

| Concern | Old | New |
|---------|-----|-----|
| Role selection | Hidden sliding overlay | In-card `RoleSelectorTabs` w/ sliding pill |
| Background | Flat `#f6f5f7` | 4-layer composition (gradient → blobs → dots → SVG) |
| Card | Opaque white, harsh shadow | Glassmorphism, refined low-opacity shadow system |
| Motion | 0.6s panel slide | 0.45s staggered entrance + 0.18s tab fade/transform |
| Trust signal | None | Feature/security list + brand lockup |
| Icons | Lucide (good) | Lucide, standardized sizing/placement |
