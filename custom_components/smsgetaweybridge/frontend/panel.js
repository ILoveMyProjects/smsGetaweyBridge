/* smsGetaweyBridge 1.0.0. Admin-only HA panel; no third-party scripts. */
const BRIDGE = 'smsgetaweybridge';
class SMSGetaweyBridgePanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:'open'});
    this.tab='overview'; this.gateways=[]; this.selection='';
    this.busy=false; this.initialized=false;
    this.editGroup=null; this.editTemplate=null;
  }
  set hass(value) { this._hass=value; if(!this.initialized){this.initialized=true;this.refresh();} }
  set panel(value) { this._panel=value; }
  el(tag,text,parent,cls) {
    const e=document.createElement(tag);
    if(text!==undefined)e.textContent=text;
    if(cls)e.className=cls;
    if(parent)parent.append(e);
    return e;
  }
  title(parent,text,subtitle) {
    const h=this.el('h2',text,parent);
    if(subtitle)this.el('p',subtitle,parent,'hint');
    return h;
  }
  field(parent,label,type='text',initial='',note='') {
    const wrapper=this.el('label',undefined,parent,'field');
    this.el('span',label,wrapper);
    const control=this.el(type==='textarea'?'textarea':'input',undefined,wrapper);
    if(type!=='textarea')control.type=type;
    control.value=initial;
    if(note)this.el('small',note,wrapper);
    return control;
  }
  btn(parent,text,fn,cls='') {
    const b=this.el('button',text,parent,cls);b.type='button';b.addEventListener('click',fn);return b;
  }
  section(parent,cls='') {return this.el('section',undefined,parent,cls);}
  select(parent,entries,value,cb) {
    const s=this.el('select',undefined,parent);
    for(const entry of entries){const o=this.el('option',entry.label,s);o.value=entry.value;}
    if(value!==undefined)s.value=value;
    if(cb)s.addEventListener('change',()=>cb(s.value));
    return s;
  }
  async refresh() {
    try {
      this.gateways=await this._hass.callWS({type:`${BRIDGE}/list`});
      if(!this.gateways.some(x=>x.entry_id===this.selection))this.selection=this.gateways[0]?.entry_id||'';
      this.render();
    } catch(e){this.render();this.notify(e.message||'Cannot load SMS Bridge');}
  }
  notify(message) {
    const target=this.shadowRoot.querySelector('#notice');
    if(target){target.textContent=message;target.setAttribute('role','status');}
  }
  async invoke(action,data) {
    return this._hass.callWS({type:`${BRIDGE}/${action}`,entry_id:this.selection,...data});
  }
  async save(op,success='Saved successfully') {
    if(this.busy)return;
    this.busy=true;
    try {await op();await this.refresh();this.notify(success);}
    catch(err){this.notify(`Error: ${err.message||'Operation failed'}`);}
    finally {this.busy=false;}
  }
  render() {
    const root=this.shadowRoot;root.replaceChildren();
    this.el('style',`
      :host{display:block;min-height:100%;background:var(--primary-background-color,#f6f7f9);color:var(--primary-text-color,#222);font:inherit}
      *{box-sizing:border-box}main{max-width:1120px;margin:auto;padding:20px}header{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap}
      h1{font-size:1.7rem;margin:0}h2{font-size:1.18rem;margin:4px 0 8px}h3{font-size:1rem;margin:6px 0}p{line-height:1.5}
      .hero{margin:10px 0 18px}.hint,small{font-size:.88rem;opacity:.8;line-height:1.45}small{display:block;margin-top:6px}
      .panel,section{border:1px solid var(--divider-color,#ddd);border-radius:13px;padding:19px;background:var(--card-background-color,#fff);margin:12px 0}
      .columns{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:14px}.columns>section{margin:0}
      nav{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0 8px}.pill{border:1px solid var(--divider-color,#aaa);border-radius:99px;padding:9px 18px;background:transparent}
      .selected{color:var(--primary-color,#0099e5);border-color:var(--primary-color,#0099e5);font-weight:700}
      button,textarea,input,select{font:inherit;color:inherit;border:1px solid var(--divider-color,#aaa);border-radius:8px;background:var(--card-background-color,#fff);padding:10px}
      button{cursor:pointer;width:auto}button:hover{filter:brightness(.92)}button.primary{background:var(--primary-color,#0389cd);color:var(--text-primary-color,#fff);border-color:transparent}
      button.danger{color:var(--error-color,#d33)}.field{display:block;margin:14px 0}.field>span{font-weight:600;display:block;margin-bottom:5px}
      .field input,.field textarea,.field select{width:100%}textarea{min-height:100px;resize:vertical}select{max-width:100%}
      .toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.row{padding:13px 0;border-bottom:1px solid var(--divider-color,#ddd);display:flex;justify-content:space-between;gap:12px;align-items:start;flex-wrap:wrap}
      .row:last-child{border:0}.tag{border-radius:100px;background:var(--secondary-background-color,#eee);padding:5px 10px;display:inline-block;margin:3px;font-size:.81rem}
      .ok{color:var(--success-color,#14883b)}.problem{color:var(--error-color,#d33)}.status{padding:12px 16px;border-radius:10px;background:var(--secondary-background-color,#f0f1f5)}
      .metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:14px 0}.metric{padding:16px;border-radius:10px;background:var(--secondary-background-color,#eee)}
      .metric strong{font-size:1.3rem;display:block}.muted{opacity:.72}code{font-family:monospace;overflow-wrap:anywhere}
      .warning{border-left:4px solid var(--warning-color,#df8a17);padding:12px;background:var(--secondary-background-color,#f3f1ea)}
      details{margin:12px 0}summary{cursor:pointer;font-weight:600}#notice{min-height:1.4em;color:var(--primary-color,#0389cd)}
      @media(max-width:600px){main{padding:12px}.panel,section{padding:14px}header{align-items:stretch}}
    `,root);
    const main=this.el('main',undefined,root);const head=this.el('header',undefined,main);
    this.el('h1','✉ smsGetaweyBridge',head);
    const opts=this.gateways.map(g=>({value:g.entry_id,label:g.title}));
    this.select(head,opts,this.selection,v=>{this.selection=v;this.render();});
    this.btn(head,'↻ Refresh',()=>this.refresh());
    this.el('p','',main).id='notice';
    const nav=this.el('nav',undefined,main);
    for(const [key,label] of [['overview','Overview'],['templates','Templates & Groups'],['logs','Activity & Logs']]){
      this.btn(nav,label,()=>{this.tab=key;this.render();},'pill '+(this.tab===key?'selected':''));
    }
    const g=this.gateways.find(x=>x.entry_id===this.selection);
    if(!g){this.el('section','Add the Local Server via Settings → Devices & services → Add integration → smsGetaweyBridge.',main);return;}
    if(this.tab==='overview')this.overview(main,g);
    if(this.tab==='templates')this.templates(main,g);
    if(this.tab==='logs')this.logs(main,g);
  }
  overview(main,g) {
    this.title(main,'Overview','Gateway connection, automatic webhook registration and a quick SMS composer. No Ubuntu manager is required.');
    const m=this.el('div',undefined,main,'metrics');
    for(const [label,value] of [['Gateway',g.online?'Online':'Offline'],['Received (loaded)',g.inbox_count],['Sent (loaded)',g.outgoing_count],['Webhook',g.webhook_status||'not configured']]){
      const item=this.el('div',undefined,m,'metric');this.el('small',label,item);this.el('strong',String(value),item);
    }
    const info=this.section(main);this.el('h2','How SMS Bridge works',info);
    this.el('p','Home Assistant communicates directly with the Android SMS Gateway Local Server. Sent messages are recorded by gateway ID and marked homeassistant; other clients (including Ubuntu) remain external/unknown unless proven otherwise.',info);
    this.el('p','Incoming messages and delivery statuses are read periodically even when webhooks are unavailable.',info,'hint');
    const hook=this.section(main);this.el('h2','Automatic local webhook setup',hook);
    const states={registered:'Registered with your phone. Notifications are sent to your Home Assistant endpoint.',unavailable_local_https:'No internal HTTPS URL is configured in Home Assistant. Webhook cannot be registered securely. Polling is active.',registration_failed:'The phone rejected or could not complete webhook registration. Check local HTTPS certificate trust and Gateway Local Server permissions. Polling is active.',not_configured:'Not configured. Polling remains active.'};
    this.el('p',states[g.webhook_status]||'Current state: '+g.webhook_status,hook,g.webhook_status==='registered'?'ok':'warning');
    this.el('small','No URL needs to be pasted. The integration discovers the internal HA HTTPS URL after login. It never changes firewall rules or connects to the SMS Gateway cloud. Android requires a trusted HTTPS certificate for non-loopback webhook destinations.',hook);
    const compose=this.section(main);this.el('h2','Send an SMS now',compose);
    this.el('p','Direct one-off message. To send a reusable message to a saved recipient group, use Templates & Groups.',compose,'hint');
    const recipient=this.field(compose,'Recipient phone number','text','', 'Use international format, for example +441234567890.');
    const body=this.field(compose,'Message','textarea','');
    this.btn(compose,'Send SMS',()=>{
      if(!recipient.value.trim()||!body.value.trim()){this.notify('Enter number and SMS text');return;}
      if(!confirm('Send one paid SMS to '+recipient.value.trim()+'?'))return;
      this.save(()=>this.invoke('send_sms',{phone_number:recipient.value.trim(),message:body.value}),'SMS submitted. View Activity & Logs for its status.');
    },'primary');
  }
  templates(main,g) {
    this.title(main,'Templates & Groups','Create groups of recipients, edit reusable SMS templates, and see exactly which variables each template requires.');
    const cols=this.el('div',undefined,main,'columns');
    const groups=this.section(cols);this.el('h2','1 · Recipient groups',groups);
    this.el('p','A group is a named list of phone numbers. Templates send to every number in their selected group.',groups,'hint');
    for(const [name,nums] of Object.entries(g.groups).sort(([a],[b])=>a.localeCompare(b))){
      const row=this.el('div',undefined,groups,'row');const info=this.el('div',undefined,row);
      this.el('strong',name,info);this.el('small',`${nums.length} recipient(s)`,info);
      const controls=this.el('div',undefined,row,'toolbar');
      this.btn(controls,'Edit',()=>{this.editGroup=name;this.render();});
      this.btn(controls,'Delete',()=>{if(confirm(`Delete recipient group ${name}?`))this.save(()=>this.invoke('edit',{kind:'group',name,value:null}));},'danger');
    }
    this.el('h3',this.editGroup?'Edit group':'Create group',groups);
    const gn=this.field(groups,'Group key','text',this.editGroup||'', 'Letters, digits, underscore. Existing keys cannot be renamed here.');
    if(this.editGroup)gn.disabled=true;
    const gp=this.field(groups,'Recipients (one per line or comma separated)','textarea',this.editGroup?(g.groups[this.editGroup]||[]).join('\n'):'');
    this.btn(groups,'Save group',()=>this.save(async()=>{
      await this.invoke('edit',{kind:'group',name:gn.value.trim(),value:gp.value.split(/[\n,;]/).map(s=>s.trim()).filter(Boolean)});
      this.editGroup=null;
    }),'primary');
    if(this.editGroup)this.btn(groups,'Cancel editing',()=>{this.editGroup=null;this.render();});
    const templates=this.section(cols);this.el('h2','2 · Saved SMS templates',templates);
    this.el('p','Use $variable or ${variable} in the body. All required variable names are listed automatically. $$ prints a literal $.',templates,'hint');
    for(const [name,t] of Object.entries(g.templates).sort(([a],[b])=>a.localeCompare(b))){
      const row=this.el('div',undefined,templates,'row');const detail=this.el('div',undefined,row);
      this.el('strong',name,detail);this.el('small',`Group: ${t.group}`,detail);
      for(const variable of g.template_variables?.[name]||[])this.el('span','$'+variable,detail,'tag');
      if(!(g.template_variables?.[name]||[]).length)this.el('small','No variables',detail);
      const controls=this.el('div',undefined,row,'toolbar');
      this.btn(controls,'Edit',()=>{this.editTemplate=name;this.render();});
      this.btn(controls,'Delete',()=>{if(confirm(`Delete SMS template ${name}?`))this.save(()=>this.invoke('edit',{kind:'template',name,value:null}));},'danger');
    }
    this.el('h3',this.editTemplate?'Edit template':'Create template',templates);
    const curr=this.editTemplate?g.templates[this.editTemplate]:null;
    const tn=this.field(templates,'Template key','text',this.editTemplate||'');if(curr)tn.disabled=true;
    this.el('small','Recipient group for this template:',templates);
    const select=this.select(templates,Object.keys(g.groups).sort().map(x=>({value:x,label:x})),curr?.group);
    const body=this.field(templates,'SMS text with $variables','textarea',curr?.body||'');
    const preview=this.el('p','',templates,'hint');
    const extract=()=>{
      const text=body.value.replace(/\$\$/g,'');
      const names=[...new Set([...text.matchAll(/\$\{([A-Za-z][A-Za-z0-9_]*)\}|\$([A-Za-z][A-Za-z0-9_]*)/g)].map(m=>m[1]||m[2]))];
      preview.textContent=names.length?'Required variables: '+names.map(x=>'$'+x).join(', '):'No variables required.';
    };
    body.addEventListener('input',extract);extract();
    this.btn(templates,'Save template',()=>this.save(async()=>{
      await this.invoke('edit',{kind:'template',name:tn.value.trim(),value:{group:select.value,body:body.value}});this.editTemplate=null;
    }),'primary');
    if(this.editTemplate)this.btn(templates,'Cancel editing',()=>{this.editTemplate=null;this.render();});
    const test=this.section(main);this.el('h2','3 · Use a saved template',test);
    this.el('p','Choose a template. Fill the generated fields below. The same templates appear in Home Assistant automation actions under “Send saved SMS template” and as individual “Send SMS: …” actions with named variable fields.',test,'hint');
    const items=Object.entries(g.templates).sort(([a],[b])=>a.localeCompare(b));
    const ts=this.select(test,items.map(([k,t])=>({value:k,label:`${k} → ${t.group}`})),items[0]?.[0]);
    const target=this.el('div',undefined,test);
    const variableInputs=new Map();
    const updateVars=()=>{
      target.replaceChildren();variableInputs.clear();
      const current=g.templates[ts.value];if(!current)return;
      this.el('p','Template text: '+current.body,target,'hint');
      const names=g.template_variables?.[ts.value]||[];
      if(!names.length)this.el('small','No variables required for this template.',target);
      for(const name of names)variableInputs.set(name,this.field(target,`$${name} (required)`));
    };
    ts.addEventListener('change',updateVars);updateVars();
    this.btn(test,'Send template to its group',()=>{
      if(!ts.value){this.notify('Create a template first');return;}
      const values=Object.fromEntries([...variableInputs].map(([name,input])=>[name,input.value]));
      if(Object.values(values).some(v=>!v.trim())){this.notify('Fill every required variable');return;}
      const count=g.groups[g.templates[ts.value].group]?.length||0;
      if(!confirm(`Send ${count} paid SMS message(s) using ${ts.value}?`))return;
      this.save(()=>this.invoke('send_template',{template:ts.value,variables:values}),'SMS submitted. Check Activity & Logs for delivery status.');
    },'primary');
    this.el('small','Editing templates affects future runs of existing automations. No SMS is sent simply by saving a template.',test);
  }
  logs(main,g) {
    this.title(main,'Activity & Logs','Inspect SMS requests, incoming events, delivery reports and the sending source.');
    const s=this.section(main);this.el('h2','Understanding the activity journal',s);
    this.el('p','Queued means the gateway accepted the request, not that the recipient received it. Sent means the phone sent the SMS; Delivered requires a delivery report from the network. Failed means the gateway reports a sending error.',s);
    this.el('p','Source homeassistant: submitted by HA. Source external/unknown: not submitted by HA (this may include Ubuntu Server or other tools; the exact external system cannot be proven).',s,'hint');
    this.el('small','Only the most recent 100 records are shown. SMS text and complete numbers are not stored in these diagnostic logs.',s);
    if(!g.logs.length){this.el('p','No activity recorded yet. New records appear when sending or receiving messages.',s,'muted');return;}
    for(const record of g.logs){
      const row=this.el('div',undefined,s,'row');const body=this.el('div',undefined,row);
      this.el('strong',`${record.type} • ${record.source}`,body);
      this.el('small',`${record.when} · Message ID: ${record.message_id} ${record.detail||''}`,body);
    }
  }
}
customElements.define('smsgetaweybridge-panel', SMSGetaweyBridgePanel);
