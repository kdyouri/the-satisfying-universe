// Contract-derived local Google upload stand-in; synthetic credentials and media only.
const http = require('http');
let mode = 'success', events = [], upload = null, listing = 0, existing = null;
let multiple=false, uploads={}, sessions={}, sequence=0, publicBase='http://127.0.0.1:4012/youtube-upload';
let staleResource=null;
async function raw(req) {
  if (req.body !== undefined) {
    if (Buffer.isBuffer(req.body)) return req.body;
    return Buffer.from(typeof req.body === 'string' ? req.body : JSON.stringify(req.body));
  }
  const chunks = [];
  for await (const chunk of req) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks);
}
function send(res, status, value, headers={}) {
  res.writeHead(status, {'Content-Type':'application/json','X-TSU-Mock':'youtube-upload',...headers});
  res.end(value === null ? '' : JSON.stringify(value));
}
function resource(job=upload) {
  if (existing) return structuredClone(existing);
  return {id:job.id || 'testVideo01', localizations:job.metadata.localizations || {}, snippet:{...job.metadata.snippet,tags:[...(job.metadata.snippet.tags || [])].sort(),channelId:'UC8DbuevZRxVTWxltG9oDFRw'},
    status:{...job.metadata.status,uploadStatus:'processed'},
    contentDetails:{duration:'PT16S',definition:'hd'},
    processingDetails:{processingStatus:mode === 'processing_failure' ? 'failed' :
      mode === 'processing_delay' && listing < 2 ? 'processing' : 'succeeded'}};
}
function progress(res) {
  if (upload.done) return send(res, 200, resource());
  return send(res, 308, null, upload.bytes ? {'Range':`bytes=0-${upload.bytes-1}`} : {});
}
http.createServer(async (req,res) => {
  const url = new URL(req.url,'http://127.0.0.1');
  if (url.pathname === '/__control') {
    if (req.method === 'POST') {
      const options=JSON.parse((await raw(req)).toString());
      if (options.preserve) { mode=options.mode; return send(res,200,{mode,events}); }
      const previous=options.existing ? resource() : null;
      mode=options.mode;events=[];upload=null;listing=0;existing=previous;staleResource=null;
      multiple=!!options.multiple;uploads={};sessions={};sequence=0;
      publicBase=options.base_url || 'http://127.0.0.1:4012/youtube-upload';
      if (existing) {
        existing.snippet.categoryId='28'; existing.snippet.tags=['keep-tag'];
        existing.status.license='youtube'; existing.status.embeddable=false;
        existing.status.publicStatsViewable=false;
        existing.localizations={de:{title:'Bestehender Titel',description:'Beibehalten'}};
      }
    }
    return send(res,200,{mode,events,upload:upload ? {bytes:upload.bytes,done:upload.done}:null});
  }
  const bytes = await raw(req);
  events.push({method:req.method,path:url.pathname,range:req.headers['content-range'],
    bytes:bytes.length,declared_bytes:Number(req.headers['content-length'] || 0)});
  if (url.pathname === '/token') {
    const body=Object.fromEntries(new URLSearchParams(bytes.toString()));
    if (body.grant_type !== 'refresh_token' || body.client_id !== 'fake.apps.googleusercontent.com'
        || body.refresh_token !== 'fake-refresh' || body.client_secret !== 'fake-secret') {
      return send(res,400,{error:'invalid_request'});
    }
    if (mode === 'revoked_grant') return send(res,400,{error:'invalid_grant'});
    return send(res,200,{access_token:'fake-upload-access',expires_in:3600});
  }
  if (req.headers.authorization !== 'Bearer fake-upload-access') return send(res,401,{error:{}});
  if (url.pathname === '/youtube/v3/channels') {
    return send(res,200,{items:[{id:mode === 'wrong_channel' ? 'UCwrong' : 'UC8DbuevZRxVTWxltG9oDFRw',
      snippet:{customUrl:'@techno-inno'}}]});
  }
  if (url.pathname === '/youtube/v3/videos' && req.method === 'PUT') {
    const body=JSON.parse(bytes.toString()), part=url.searchParams.get('part');
    const job=uploads[body.id];
    const target=existing || (job ? resource(job) : null);
    events[events.length-1].body=body; events[events.length-1].part=part;
    if (!target || body.id !== target.id) return send(res,404,{error:{}});
    if (part === 'snippet,localizations') {
      if (mode === 'metadata_error') return send(res,400,{error:{errors:[{reason:'invalidTitle'}]}});
      if ('status' in body) return send(res,400,{error:{}});
      if (mode === 'stale_metadata_read') staleResource=structuredClone(target);
      target.snippet={...target.snippet,...body.snippet};
      target.localizations=body.localizations;
      if (job) job.metadata={...job.metadata,snippet:target.snippet,localizations:target.localizations};
      if (mode === 'metadata_mismatch') delete existing.localizations['zh-CN'];
      if (mode === 'lost_metadata_response') {
        const saved=resource(job || upload); mode='publish_success';
        return setTimeout(()=>send(res,200,saved),1000);
      }
      return send(res,200,resource(job || upload));
    }
    if (part === 'status') {
      if (mode === 'public_error') return send(res,403,{error:{errors:[{reason:'forbidden'}]}});
      if (Object.keys(target.localizations).length < 6) return send(res,400,{error:{}});
      target.status={...target.status,...body.status};
      if (job) job.metadata.status=target.status;
      if (mode === 'lost_public_response') {
        const saved=resource(job || upload); mode='publish_success';
        return setTimeout(()=>send(res,200,saved),1000);
      }
      return send(res,200,resource(job || upload));
    }
    return send(res,501,{error:'Unmodeled update part'});
  }
  if (url.pathname === '/youtube/v3/videos' && req.method === 'GET') {
    ++listing;
    if (staleResource) {const saved=staleResource;staleResource=null;return send(res,200,{items:[saved]});}
    const known=uploads[url.searchParams.get('id')];
    const item=existing || known?.done ? resource(known || upload) : null;
    if (item && mode === 'publish_wrong_channel') item.snippet.channelId='UCwrong';
    if (item && mode === 'publish_restricted') item.contentDetails.regionRestriction={blocked:['US']};
    if (item && mode === 'publish_not_processed') {
      item.status.uploadStatus='uploaded'; item.processingDetails.processingStatus='processing';
    }
    return send(res,200,{items:item ? [item] : []});
  }
  if (url.pathname === '/upload/youtube/v3/videos' && req.method === 'POST') {
    const metadata=JSON.parse(bytes.toString());
    events[events.length-1].metadata=metadata;
    if (metadata.status.privacyStatus !== 'private' || !metadata.status.containsSyntheticMedia
        || metadata.status.selfDeclaredMadeForKids !== false
        || url.searchParams.get('notifySubscribers') !== 'false') return send(res,400,{error:{}});
    ++sequence; const id=multiple ? `jobVideo${String(sequence).padStart(3,'0')}` : 'testVideo01';
    const session=multiple ? `synthetic-session-${sequence}` : 'synthetic-session';
    upload={id,session,metadata,total:Number(req.headers['x-upload-content-length']),bytes:0,done:false,interrupted:false};
    uploads[id]=upload;sessions[session]=upload;
    const location=mode === 'bad_location' ? 'https://untrusted.invalid/upload?upload_id=fake' :
      `${publicBase}/upload/youtube/v3/videos?upload_id=${session}`;
    if (mode === 'start_timeout') return setTimeout(()=>send(res,200,null,{'Location':location}),1000);
    return send(res,200,null,{'Location':location});
  }
  if (url.pathname === '/upload/youtube/v3/videos' && req.method === 'PUT' && sessions[url.searchParams.get('upload_id')]) {
    upload=sessions[url.searchParams.get('upload_id')];
    // The local Postman gateway decodes binary bodies as text before invoking this
    // handler. Model the wire Content-Length/ranges; do not claim a media checksum.
    const transferred=Number(req.headers['content-length'] || 0);
    const range=req.headers['content-range'];
    if (range === `bytes */${upload.total}`) return progress(res);
    const match=range?.match(/^bytes (\d+)-(\d+)\/(\d+)$/);
    if (!match || Number(match[1]) !== upload.bytes || Number(match[3]) !== upload.total
        || Number(match[2])-Number(match[1])+1 !== transferred) return send(res,400,{error:{}});
    if (mode === 'partial_ack' && upload.bytes === 0 && transferred > 262144) {
      upload.bytes=262144;return progress(res);
    }
    upload.bytes += transferred;
    upload.done=upload.bytes===upload.total;
    if (mode === 'lost_completion' && upload.done && !upload.interrupted) {
      upload.interrupted=true;
      const saved=resource();return setTimeout(()=>send(res,201,saved),1000);
    }
    if (mode === 'midway_timeout' && !upload.interrupted) {
      upload.interrupted=true;
      const savedBytes=upload.bytes;
      return setTimeout(()=>send(res,308,null,{'Range':`bytes=0-${savedBytes-1}`}),1000);
    }
    return progress(res);
  }
  return send(res,501,{error:'Unmodeled endpoint'});
}).listen(process.env.PORT || 4502);
