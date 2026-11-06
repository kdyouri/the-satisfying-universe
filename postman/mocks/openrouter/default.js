// Local contract stand-in. Only synthetic credentials, media, costs and scores.
const http = require('http');
const catalogue = require('./catalogue.json');
const clip = Buffer.from(require('./clip.json'), 'base64');
const alternateClip = Buffer.from(require('./clip-alternate.json'), 'base64');
const nativeClip = Buffer.from(require('./native-clip.json'), 'base64');
const nativeSilent = Buffer.from(require('./native-silent.json'), 'base64');
const nativeClip8 = Buffer.from(require('./native-clip-8.json'), 'base64');
const nativeSilent8 = Buffer.from(require('./native-silent-8.json'), 'base64');
let mode = 'success', events = [], jobs = {}, creativeCount = 0, qaCount = 0;
async function body(req) {
  if (req.body !== undefined) return typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
  let data = '';
  for await (const chunk of req) data += chunk;
  return data ? JSON.parse(data) : {};
}
function send(res, status, value) {
  res.writeHead(status, {'Content-Type': 'application/json', 'X-TSU-Mock': 'openrouter'});
  res.end(JSON.stringify(value));
}
const brief = {
  concept: 'Une spirale dorée dans un bol sombre', title: 'Spirale dorée',
  description: 'Mouvement lent de liquide doré, création originale.', hashtags: ['#satisfying'],
  prompts: ['Golden viscous liquid spirals slowly in a matte black bowl, fixed macro camera.',
            'Continue from the first frame: same golden liquid, bowl and macro camera. Settle slowly.']
};
http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1');
  if (url.pathname === '/__control') {
    if (req.method === 'POST') { mode = (await body(req)).mode; events = []; jobs = {}; creativeCount=0; qaCount=0; }
    return send(res, 200, {mode, events, jobs});
  }
  if (req.headers.authorization !== 'Bearer synthetic-openrouter-key') return send(res, 401, {});
  const data = req.method === 'POST' ? await body(req) : {};
  events.push({method: req.method, path: url.pathname, body: data});
  if (url.pathname === '/key') return send(res, 200, {data: {limit_remaining: 100}});
  if (url.pathname === '/models') return send(res, 200, {data: catalogue.models});
  if (url.pathname === '/videos/models') {
    const videos = JSON.parse(JSON.stringify(catalogue.videos));
    if (mode === 'price_increase') videos[0].pricing_skus.duration_seconds_without_audio = '0.06';
    const native = videos.find(v => v.id === 'google/gemini-omni-1.2-flash');
    const veoNative = videos.find(v => v.id === 'google/veo-3.1-lite');
    if (mode === 'native_price_increase') {
      native.pricing_skus.duration_seconds_with_audio = '0.11';
      veoNative.pricing_skus.duration_seconds_with_audio = '0.09';
    }
    if (mode === 'native_no_audio_capability') {
      native.generate_audio = false;
      veoNative.generate_audio = false;
    }
    if (mode === 'native_no_duration') {
      native.supported_durations = [8];
      veoNative.supported_durations = [4, 6];
    }
    if (mode === 'native_unknown_price') {
      delete native.pricing_skus.duration_seconds_with_audio;
      delete veoNative.pricing_skus.duration_seconds_with_audio;
    }
    return send(res, 200, {data: videos});
  }
  if (url.pathname === '/chat/completions') {
    if (mode === 'chat_error') return send(res, 503, {error: 'synthetic'});
    const qa = data.messages[0].content.some(c => c.type === 'video_url');
    const reusable = !!data.response_format.json_schema.schema.properties.localizations;
    if (!data.response_format.json_schema.strict || data.provider.allow_fallbacks !== false
        || data.provider.require_parameters !== true) return send(res, 400, {error: 'contract'});
    const scores = {visual_realism: 23, motion_quality: 18, aesthetic_quality: 18,
      prompt_compliance: 18, technical_quality: 14, technical_pass: true, severe_defects: [],
      issues: [], audio_coherence: 'coherent'};
    if (mode === 'qa_minor' || mode === 'qa_visible_major' || mode === 'qa_uncertain') {
      scores.issues = [{start_seconds: 1.0, end_seconds: 1.4,
        severity: mode === 'qa_visible_major' ? 'major' : 'minor',
        visibility: mode === 'qa_uncertain' ? 'uncertain' : 'normal_playback',
        remedy: 'local_edit', description: 'Variation du reflet au raccord',
        evidence: 'Le reflet change de position sur le bol pendant le raccord.'}];
    }
    if (mode === 'qa_low_score') scores.motion_quality = 5;
    if (mode === 'qa_audio_unobservable') scores.audio_coherence = 'not_observable';
    let output=qa ? scores : brief;
    if (qa) ++qaCount;
    else {
      ++creativeCount;
      if (reusable) {
        const n=mode === 'duplicate_concept' ? 1 : creativeCount;
        const native = data.messages[0].content.some(c => (c.text || '').includes('NATIVE_SINGLE_GENERATION'));
        const effects = data.messages[0].content.some(c => (c.text || '').includes('Set sound_plan to kind'));
        const localizations=Object.fromEntries(['en','fr','es','it','ru','zh-CN'].map(code=>[
          code,{title:`Synthetic ${code} video ${n}`,description:`TechnoInno ${code}: AI-generated visuals. Original ${native ? 'AI-generated audio' : effects ? 'synthesized sound effects' : 'music'}. ${n}`}
        ]));
        output={...brief,concept:`Distinct synthetic concept ${n}`,title:localizations.en.title,
          description:localizations.en.description,localizations,hashtags:['#LiquidFlow','#Macro']};
        if (native) { output.prompts = [brief.prompts[0] + ' Native synchronized liquid flow sounds, no music, one continuous 15-second scene.']; output.sound_plan = null; }
        if (effects && mode !== 'sound_missing') output.sound_plan={
          kind: mode === 'sound_unsupported' ? 'needs_review' : 'liquid_flow',cues_seconds:[]};
      }
    }
    return send(res, 200, {id: qa ? `synthetic-qa-${qaCount}` : `synthetic-creative-${creativeCount}`,
      usage: {cost: qa ? 0.004 : 0.0001},
      choices: [{message: {content: JSON.stringify(output)}}]});
  }
  if (url.pathname === '/videos' && req.method === 'POST') {
    const id = `synthetic-${Object.keys(jobs).length + 1}`;
    const native = data.generate_audio === true;
    const nativeSeconds = {'google/gemini-omni-1.2-flash': 15, 'google/veo-3.1-lite': 8};
    const expectedSeconds = native ? (nativeSeconds[data.model] || 15) : 8;
    jobs[id] = {polls: 0, native, model: data.model}; // Created even in ambiguous timeout/error scenarios.
    if (data.duration !== expectedSeconds || data.resolution !== '1080p' || data.aspect_ratio !== '9:16'
        || data.generate_audio !== native || (native && data.frame_images)) return send(res, 400, {error: 'contract'});
    if (mode === 'submit_error') return send(res, 503, {error: 'synthetic'});
    if (mode === 'submit_timeout') return setTimeout(() => send(res, 202, {id}), 1000);
    return send(res, 202, {id, status: 'pending', polling_url: 'https://untrusted.invalid/ignore'});
  }
  const match = url.pathname.match(/^\/videos\/([^/]+)(\/content)?$/);
  if (match && jobs[match[1]]) {
    if (match[2]) {
      res.writeHead(200, {'Content-Type': mode === 'bad_media' ? 'text/plain' : 'video/mp4'});
      if (jobs[match[1]].native) {
        const veo = jobs[match[1]].model === 'google/veo-3.1-lite';
        return res.end(mode === 'native_silent'
          ? (veo ? nativeSilent8 : nativeSilent)
          : (veo ? nativeClip8 : nativeClip));
      }
      return res.end(Number(match[1].split('-').pop()) >= 3 ? alternateClip : clip);
    }
    const polls = ++jobs[match[1]].polls;
    if (polls === 1) return send(res, 200, {id: match[1], status: 'in_progress'});
    if (mode === 'terminal_error_body') {
      return send(res, 200, {id: match[1], status: 'failed', error: 'Video generation failed'});
    }
    const value = {id: match[1], status: mode === 'failed_video' ? 'failed' : 'completed',
      generation_id: `gen-${match[1]}`, usage: {cost: mode === 'overrun' ? 0.5
        : jobs[match[1]].native ? (jobs[match[1]].model === 'google/veo-3.1-lite' ? 0.64 : 1.56384) : 0.4}};
    if (mode === 'missing_cost') delete value.usage;
    return send(res, 200, value);
  }
  return send(res, 501, {error: 'Unmodeled endpoint'});
}).listen(process.env.PORT || 4501);
