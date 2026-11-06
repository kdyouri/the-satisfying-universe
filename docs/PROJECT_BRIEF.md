# PROJECT: THE SATISFYING UNIVERSE
## Autonomous AI Video Production Platform — Technical Implementation

You are the technical project manager, software architect, senior Python developer, AI integration engineer, DevOps engineer, and implementation assistant for this project.

Your mission is to help me design, build, configure, test, and launch a fully automated AI video production and social media publishing system, from beginning to end.

You must actively carry out the work using your available tools, browser, coding environment, and file management capabilities whenever possible. Do not simply give me instructions or theoretical recommendations. Implement the actual solution whenever you can.

I will perform manual tasks whenever they require my personal intervention, such as creating accounts, verifying identities, entering authentication codes, accepting terms, granting permissions, or providing API credentials.

Work iteratively. Keep track of completed tasks, pending tasks, decisions, blockers, and next steps.

---

# 1. PROJECT OBJECTIVE

Build an automated content production system for a brand called:

**The Satisfying Universe**

Tagline: Beautiful things. Perfect moments.

Content direction:
- Oddly satisfying videos.
- Calming and relaxing scenes.
- Hypnotic visual effects.
- Ultra-realistic macro photography.
- Miniature worlds and landscapes.
- Colorful liquids and transformations.
- Perfect movements, symmetry, and visually satisfying interactions.

Video requirements:
- Vertical 9:16 format.
- Target duration: 15–20 seconds.
- Ultra-realistic visual quality.
- Cinematic macro photography.
- Natural-looking movements and physics.
- Beautiful lighting and composition.
- No unnecessary narration or dialogue.
- No captions, logos, or watermarks unless explicitly required.

Initial production target: **2 original videos per day**.

Each video should be published automatically on:
- YouTube Shorts.
- TikTok.
- Instagram Reels.

The target is two original videos daily, potentially resulting in six publications per day across the three platforms.

The system must operate automatically once configured.

---

# 2. IMPORTANT ARCHITECTURAL DECISIONS

Use the following principles:

- OpenRouter is the central AI model provider.
- Build our own orchestration system.
- Do NOT use OpenClaw.
- Do NOT use n8n.
- Do NOT introduce unnecessary third-party orchestration platforms.
- Use Python for the backend and AI workflow.
- Use FastAPI for the application API.
- Use PostgreSQL for persistent data.
- Use Redis and Celery for asynchronous jobs.
- Use FFmpeg for video processing.
- Use Docker Compose for deployment.
- Use compatible object storage for generated videos.
- Keep the architecture modular and maintainable.

The system should allow us to change AI models and video providers without rewriting the application.

Prefer official APIs and documented integrations over fragile browser automation.

Do not assume that every video model available through OpenRouter supports the same duration, resolution, audio, or generation parameters. Discover and verify model capabilities before implementation.

---

# 3. PHASE ZERO — RESEARCH AND PROJECT PLANNING

Before coding:

1. Inspect the available environment and tools.
2. Research the current OpenRouter documentation, particularly:
   - Text generation API.
   - Video generation API.
   - Available video models.
   - Model parameters and capabilities.
   - Asynchronous job management.
   - Pricing.
   - Rate limits.
3. Research official documentation for:
   - YouTube Data API.
   - TikTok Content Posting API.
   - Instagram Graph API.
4. Verify current account requirements, API access requirements, publishing restrictions, and approval processes.
5. Compare video models for our specific content style.
6. Estimate production costs for two videos per day.
7. Identify all required manual setup tasks.

Do not rely on outdated documentation or invent API capabilities.

Create:
- ARCHITECTURE.md
- IMPLEMENTATION_PLAN.md
- COST_ESTIMATE.md
- MANUAL_TASKS.md

Present the architecture and initial decisions before beginning major implementation.

Do not wait for me to approve every technical detail. Make sensible engineering decisions and document them. Ask me only when a decision genuinely requires my preference or authorization.

---

# 4. PHASE ONE — CREATE THE BRAND'S SOCIAL MEDIA IDENTITY

I want completely separate social media accounts for this project.

Do not use or modify any of my existing personal accounts.

Help me establish:

1. A dedicated brand email address.
2. A dedicated YouTube channel.
3. A dedicated TikTok account.
4. A dedicated Instagram account.

Brand identity:
- Name: The Satisfying Universe.
- Tagline: Beautiful things. Perfect moments.

Tasks:

- Check the availability of consistent usernames.
- Suggest the best available username variations.
- Prepare the profile descriptions and biographies.
- Create a consistent profile image and visual identity.
- Prepare channel descriptions and relevant branding assets.
- Guide me through account creation.
- Configure the necessary business or creator account settings.
- Identify all required API applications and permissions.
- Prepare OAuth configuration instructions.

You may assist with browser-based account setup where possible.

However, ask me to complete sensitive steps personally, including:
- Email and phone verification.
- CAPTCHA.
- Password creation.
- Two-factor authentication.
- Acceptance of legal terms.
- Sensitive account authorization.

Never ask me to disclose passwords or authentication codes in chat.

Do not create accounts using my personal social media profiles.

Keep ownership and administrative control of all accounts with me.

---

# 5. PHASE TWO — BUILD THE AI PRODUCTION SYSTEM

Develop three specialized AI agents.

## Agent 1: Creative Director

Responsibilities:

- Generate original video concepts.
- Avoid repetitive ideas.
- Explore satisfying, relaxing, and hypnotic content.
- Evaluate visual appeal and production feasibility.
- Generate detailed English video prompts.
- Define the intended visual style and camera movements.
- Generate titles, descriptions, and hashtags.
- Maintain creative consistency with the brand.

The agent must return structured JSON.

Suggested output:

{
  "concept": "The Perfect Water Drop",
  "category": "satisfying",
  "title": "Wait for the Perfect Splash",
  "description": "...",
  "hashtags": ["#OddlySatisfying", "#Relaxing"],
  "video_prompt": "...",
  "duration_seconds": 18,
  "aspect_ratio": "9:16",
  "style": "ultra-realistic macro photography"
}

Use a configurable OpenRouter language model.

## Agent 2: Video Producer

Responsibilities:

- Receive approved creative briefs.
- Select an appropriate video model.
- Generate videos through OpenRouter.
- Monitor asynchronous generation jobs.
- Retrieve generated files.
- Store the original video.
- Record the model, parameters, duration, and cost.
- Retry failed generations within configured limits.

Implement a provider abstraction so we can change video models without changing the business logic.

Benchmark at least three suitable video models before choosing the default model.

Consider both visual quality and cost.

Do not assume a model supports our desired duration or aspect ratio without checking its documentation.

## Agent 3: Quality Controller

Responsibilities:

- Check the technical integrity of the generated video.
- Verify duration and aspect ratio.
- Check resolution and frame rate.
- Extract representative frames.
- Analyze the visual quality using a multimodal model.
- Detect flickering, morphing, visual artifacts, unnatural movements, and prompt mismatches.
- Evaluate realism and aesthetic quality.

Implement a quality score out of 100.

Suggested scoring:
- Visual realism: 25 points.
- Motion quality: 20 points.
- Aesthetic quality: 20 points.
- Prompt compliance: 20 points.
- Technical quality: 15 points.

Minimum publication score: 80/100.

If a video fails:
- Request a new generation.
- Allow a maximum of two generation attempts per concept by default.
- If it still fails, move it to a rejected/quarantine folder.
- Record the reason for rejection.

Do not publish technically broken or clearly defective videos.

---

# 6. PHASE THREE — VIDEO POST-PRODUCTION

Use FFmpeg for:

- Vertical video formatting.
- Resolution and frame rate normalization.
- Audio handling.
- Audio normalization when appropriate.
- Trimming or combining clips if necessary.
- Final MP4 encoding.
- Technical validation.

Preserve the original generated file.

Create a final optimized version suitable for all three platforms.

Avoid unnecessary editing that could degrade the original visual quality.

---

# 7. PHASE FOUR — AUTOMATIC SOCIAL MEDIA PUBLISHING

Implement separate publishing modules:

- YouTubePublisher.
- TikTokPublisher.
- InstagramPublisher.

Use official APIs.

Responsibilities:

- Upload the video.
- Add the appropriate title and description.
- Add hashtags.
- Configure visibility and publishing settings.
- Handle API errors.
- Track publication IDs and URLs.
- Store publication status.
- Retry temporary failures safely.

Important:
- Verify API access and publishing permissions before implementation.
- Identify restrictions on private/public publishing.
- Do not assume that all platforms permit fully automated publication without review or approval.
- Avoid duplicate posts when retries occur.
- Keep each platform's credentials isolated and securely stored.

If an API requires additional approval, prepare the application and documentation and ask me to complete the necessary manual steps.

Do not bypass platform restrictions.

---

# 8. PHASE FIVE — ORCHESTRATION AND SCHEDULING

Implement a reliable daily production workflow.

Target:
- Two original videos per day.
- Publish each video to all three platforms.
- Up to six publications daily.

The scheduler must:

1. Start the production workflow.
2. Generate creative concepts.
3. Avoid recent duplicates.
4. Generate video prompts.
5. Submit video generation jobs.
6. Monitor generation status.
7. Download completed videos.
8. Run technical checks.
9. Run AI quality analysis.
10. Regenerate rejected videos when allowed.
11. Produce final MP4 files.
12. Generate publication metadata.
13. Publish to connected platforms.
14. Record all results and costs.

Implement:
- Retry policies.
- Timeouts.
- Rate-limit handling.
- Duplicate prevention.
- Daily budget limits.
- Job locking.
- Error logging.
- Persistent job states.
- Recovery after service restarts.

The system must never silently lose a production task.

If the daily budget is exhausted, stop new paid generation requests and notify me.

---

# 9. PHASE SIX — DATABASE AND FILE ORGANIZATION

Design a PostgreSQL database with tables for:

- concepts
- prompts
- video_generations
- videos
- quality_checks
- social_accounts
- publications
- analytics
- model_usage
- production_jobs
- system_settings

Record:
- Prompt and concept.
- Model used.
- Generation parameters.
- Generation duration.
- API costs.
- Quality score.
- Rejection reason.
- Final file location.
- Publication URLs.
- Publication timestamps.
- Performance metrics.

Use a clear file structure:

the-satisfying-universe/
  ideas/
  prompts/
  generated/
  approved/
  rejected/
  publications/
  analytics/

Use persistent storage and backups.

---

# 10. PHASE SEVEN — MONITORING AND ANALYTICS

Build a simple web administration interface.

It should display:

- Daily production count.
- Generated videos.
- Approved and rejected videos.
- Publication status.
- API usage and costs.
- Errors and retries.
- Daily and monthly spending.
- Platform publication links.

Collect available social media metrics:
- Views.
- Likes.
- Comments.
- Shares.
- Average watch time.
- Retention, where available.
- Follower growth.

Analyze performance to identify successful concepts and visual styles.

Use these insights to improve future creative prompts.

Do not claim that the system can access metrics that the platform APIs do not expose.

---

# 11. SECURITY AND COST CONTROL

Security is essential.

- Never hardcode API keys.
- Use environment variables and secure secret storage.
- Never commit credentials to Git.
- Provide a .env.example file without real secrets.
- Use separate credentials for each platform.
- Protect administrative endpoints.
- Configure HTTPS for production.
- Implement backup procedures.

Financial controls:

- Set a configurable daily and monthly budget.
- Track every paid AI request.
- Limit regeneration attempts.
- Avoid duplicate API calls.
- Stop generation if the budget is reached.
- Require my explicit authorization before subscribing to paid services, purchasing credits, or incurring new commitments.

Start with a configurable budget; propose an appropriate amount after researching actual model pricing.

---

# 12. WORKING METHOD — IMPORTANT

I want you to actively execute this project, not just describe how I could build it.

Follow these rules:

1. Break the project into small, manageable milestones.
2. Complete each milestone as much as possible before requesting my intervention.
3. Use your available coding tools to create actual files and implement actual code.
4. Use the browser to research official documentation and assist with account setup.
5. Run tests and verify implementations.
6. Do not claim something works unless it has been tested.
7. Maintain a project progress document.
8. Keep a list of manual tasks requiring my participation.
9. When you need me to perform a task, explain:
   - What I need to do.
   - Why it is necessary.
   - Where I need to do it.
   - What information or result I should provide afterward.
10. After I complete a manual task, continue from where you stopped.
11. Do not repeatedly ask for information already provided.
12. Make reasonable technical decisions without unnecessary questions.
13. Do not publish experimental or defective videos.
14. Do not spend money or make irreversible external changes without my authorization.

Create and maintain:
- PROJECT_STATUS.md
- DECISIONS.md
- MANUAL_TASKS.md
- IMPLEMENTATION_PLAN.md

At the end of each working session, provide:
- Completed tasks.
- Current project status.
- Files created or modified.
- Tests performed and their results.
- Remaining blockers.
- The next concrete task.

---

# 13. FIRST ACTION

Start by performing Phase Zero.

Research the current APIs and capabilities, prepare the technical architecture, evaluate video model options, estimate costs for two videos per day, and identify the manual account creation and authorization steps.

Then present the initial plan and start implementing the first milestone.

My goal is to build a reliable, maintainable, cost-controlled, fully automated AI video production business, not just a demonstration or prototype.

Take ownership of the technical execution and guide me through every manual step until the complete system is operational.