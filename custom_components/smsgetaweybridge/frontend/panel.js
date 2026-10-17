/* smsGetaweyBridge admin panel. No remote scripts, no third-party CDN. */
const TYPE = 'smsgetaweybridge';
class SMSGetaweyBridgePanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.tab = 'overview';
    this.gateways = [];
    this.selection = '';
    this.busy = false;
    this.initialized = false;
  }
  set hass(hass) {
    this._hass = hass;
    if (!this.initialized) {
      this.initialized = true;
      this.refresh();
    }
  }
  set panel(value) { this._panel = value; }
  async refresh() {
    try {
      this.gateways = await this._hass.callWS({ type: `${TYPE}/list` });
      if (!this.gateways.find(x => x.entry_id === this.selection)) {
        this.selection = this.gateways[0]?.entry_id || '';
      }
      this.render();
    } catch (e) { this.notify(e.message || 'Cannot load bridge'); }
  }
  notify(message) {
    const target = this.shadowRoot.querySelector('#notice');
    if (target) target.textContent = message;
    else { this.render(); this.shadowRoot.querySelector('#notice').textContent = message; }
  }
  elem(tag, text, parent, cls) {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (cls) el.className = cls;
    if (parent) parent.append(el);
    return el;
  }
  field(parent, label, type='text', initial='') {
    const wrap = this.elem('label', '', parent, 'field');
    this.elem('span', label, wrap);
    const input = this.elem(type === 'textarea' ? 'textarea':'input', '', wrap);
    if (type !== 'textarea') input.type = type;
    input.value = initial;
    return input;
  }
  button(parent, label, action) {
    const b = this.elem('button', label, parent); b.addEventListener('click', action); return b;
  }
  async invoke(type, data) {
    try {
      this.busy = true;
      return await this._hass.callWS({ type: `${TYPE}/${type}`, entry_id:this.selection, ...data });
    } finally { this.busy = false; }
  }
  async handle(action, ok = 'Saved') {
    if (this.busy) return;
    try { await action(); await this.refresh(); this.notify(ok); }
    catch (e) { this.notify(`Error: ${e.message || 'request failed'}`); }
  }
  render() {
    const r = this.shadowRoot; r.replaceChildren();
    const style = this.elem('style', `
      :host{display:block;background:var(--primary-background-color,#f5f5f5);min-height:100%;color:var(--primary-text-color,#222);font:inherit}
      main{max-width:980px;margin:auto;padding:24px} header{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center}
      section,.card{background:var(--card-background-color,#fff);padding:16px;border-radius:12px;margin:12px 0;box-shadow:0 1px 4px #0002}
      nav{display:flex;gap:8px;margin-top:18px} button,select,input,textarea{font:inherit;border:1px solid var(--divider-color,#bbb);border-radius:6px;padding:9px;background:var(--card-background-color,#fff);color:inherit}
      button{cursor:pointer} button.active{border:2px solid var(--primary-color,#03a9f4)} input,textarea,select{box-sizing:border-box;width:100%}
      .field{display:block;margin:10px 0}.field span{display:block;font-weight:500;margin-bottom:4px}
      .cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
      .muted{opacity:.75}.entry{padding:10px;border-bottom:1px solid var(--divider-color,#ddd)}small{display:block;opacity:.8} code{overflow-wrap:anywhere}
      #notice{min-height:1.5em} .bad{color:var(--error-color,#d32f2f)}
    `, r);
    const main=this.elem('main', '', r); const hdr=this.elem('header','',main);
    this.elem('h2','smsGetaweyBridge',hdr);
    const sel=this.elem('select','',hdr);
    for(const g of this.gateways){const opt=this.elem('option',g.title,sel);opt.value=g.entry_id;}
    sel.value=this.selection; sel.onchange=()=>{this.selection=sel.value;this.render();};
    this.button(hdr,'Refresh',()=>this.refresh());
    this.elem('p','',main).id='notice';
    const nav=this.elem('nav','',main);
    for(const [id,title] of [['overview','Overview'],['templates','Templates'],['logs','Logs']]){
      const b=this.button(nav,title,()=>{this.tab=id;this.render();});if(this.tab===id)b.className='active';
    }
    const g=this.gateways.find(x=>x.entry_id===this.selection);
    if(!g){this.elem('section','No configured gateways. Add Local Server in Settings → Devices & services.',main);return;}
    if(this.tab==='overview')this.overview(main,g);
    if(this.tab==='templates')this.templates(main,g);
    if(this.tab==='logs')this.logs(main,g);
  }
  overview(main,g){
    const section=this.elem('section','',main);
    this.elem('h3','Gateway',section);
    this.elem('p',g.online?'Online':'Offline',section,g.online?'':'bad');
    this.elem('p',`Recent inbox: ${g.inbox_count} • Recent outgoing: ${g.outgoing_count}`,section);
    this.elem('small','Polling is the fallback for received SMS and status changes. External messages are never assumed to be from Ubuntu.',section);
    this.elem('h3','Optional local HTTPS webhook',section);
    this.elem('p',g.webhook_enabled?'Webhook registered':'Polling only (webhook not enabled)',section);
    const origin=this.field(section,'Internal HTTPS Home Assistant origin (e.g. https://ha.example.lan:8123)');
    this.button(section,'Register local webhooks',()=>this.handle(()=>this.invoke('enable_webhook',{https_origin:origin.value.trim()}),'Webhook registration sent to SMS Gateway'));
    this.elem('small','Requires HTTPS trusted by the phone and a local-only HA endpoint. No public internet, cloudhook, or router forwarding is configured.',section);
    this.elem('small','Entities are listed under Settings → Devices & services → smsGetaweyBridge.',section);
  }
  templates(main,g){
    const cols=this.elem('div','',main,'cols');
    const groups=this.elem('section','',cols);this.elem('h3','Recipient groups',groups);
    for(const [name,nums] of Object.entries(g.groups)){
      const row=this.elem('div',`${name}: ${nums.length} recipients`,groups,'entry');
      this.button(row,'Remove',()=>this.handle(()=>this.invoke('edit',{kind:'group',name,value:null})));
    }
    const gn=this.field(groups,'Group key (letters, digits, underscore)');
    const phones=this.field(groups,'Numbers (comma separated, international format)');
    this.button(groups,'Save group',()=>this.handle(()=>this.invoke('edit',{kind:'group',name:gn.value.trim(),value:phones.value.split(',').map(x=>x.trim()).filter(Boolean)})));
    const templates=this.elem('section','',cols);this.elem('h3','SMS templates',templates);
    for(const [name,t] of Object.entries(g.templates)){
      const row=this.elem('div',`${name} → ${t.group}`,templates,'entry');
      this.button(row,'Remove',()=>this.handle(()=>this.invoke('edit',{kind:'template',name,value:null})));
    }
    const tn=this.field(templates,'Template key');
    const tg=this.elem('select','',templates);for(const name of Object.keys(g.groups)){const op=this.elem('option',name,tg);op.value=name;}
    const tb=this.field(templates,'Message text (use $variable placeholders)','textarea');
    this.button(templates,'Save template',()=>this.handle(()=>this.invoke('edit',{kind:'template',name:tn.value.trim(),value:{group:tg.value,body:tb.value}})));
    const send=this.elem('section','',main);this.elem('h3','Send saved template',send);
    const ts=this.elem('select','',send);for(const name of Object.keys(g.templates)){const op=this.elem('option',name,ts);op.value=name;}
    const vars=this.field(send,'Variables as JSON object, e.g. {"entity":"server"}','textarea','{}');
    this.button(send,'Send SMS (may incur charges)',()=>{
      if(!ts.value){this.notify('Choose a template first');return;}
      if(!confirm(`Send template ${ts.value} to its entire group? SMS may be charged.`))return;
      return this.handle(async()=>{
      const v=JSON.parse(vars.value); if(!v||Array.isArray(v)||typeof v!=='object')throw Error('Variables must be a JSON object');
      await this.invoke('send_template',{template:ts.value,variables:v});
    },'Request completed; check Logs for IDs and delivery status');});
    this.elem('small','Templates and groups are saved inside Home Assistant. They are not sent to Ubuntu. Sender ID remains the SIM number.',send);
  }
  logs(main,g){
    const section=this.elem('section','',main);this.elem('h3','Activity log',section);
    this.elem('small','Last 100 events; no SMS bodies or full phone numbers are logged. Admin access only.',section);
    for(const record of g.logs){
      const row=this.elem('div','',section,'entry');
      this.elem('strong',`${record.type} — ${record.source}`,row);
      this.elem('small',`${record.when} • ID ${record.message_id} • ${record.detail||''}`,row);
    }
    if(!g.logs.length)this.elem('p','No activity recorded yet.',section,'muted');
  }
}
customElements.define('smsgetaweybridge-panel',SMSGetaweyBridgePanel);
