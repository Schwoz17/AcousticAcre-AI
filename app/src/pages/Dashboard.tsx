import { ArrowUpRight, AudioWaveform, Camera, CheckCircle2, ChevronRight, Clock3, CloudOff, Leaf, Mic2, ShieldCheck, Sprout, Volume2, Wifi, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';
import { getHistory } from '../services/storage';

export default function Dashboard(){
 const history=getHistory();
 const cropCount=history.filter(x=>x.domain==='crop').length;
 const machineCount=history.filter(x=>x.domain==='machine').length;
 const recent=history.slice(0,3);
 return <div className="page-stack dashboard-page">
  <section className="hero-v2">
   <div className="hero-v2-copy"><div className="hero-overline"><span className="hero-pulse"/> FARM INTELLIGENCE, MADE ACCESSIBLE</div><h1>Know your farm.<br/><em>Grow with confidence.</em></h1><p>Practical crop and machine guidance, designed around the realities of African farming.</p><div className="hero-actions"><Link to="/crop" className="hero-primary"><Camera size={17}/> Check crop health <ArrowUpRight size={16}/></Link><Link to="/machine" className="hero-secondary"><AudioWaveform size={17}/> Listen to a machine</Link></div><div className="hero-proof"><span><ShieldCheck size={15}/> Honest when unsure</span><span><CloudOff size={15}/> Built for low connectivity</span></div></div>
   <div className="hero-visual" aria-hidden="true"><div className="hero-orbit orbit-one"/><div className="hero-orbit orbit-two"/><div className="hero-sun"/><div className="hero-land land-one"/><div className="hero-land land-two"/><div className="hero-leaf leaf-a">🌿</div><div className="hero-leaf leaf-b">🌱</div><div className="hero-float-card"><div className="float-icon"><Sprout size={18}/></div><div><b>Better decisions</b><span>Start with a simple check</span></div><CheckCircle2 size={18}/></div></div>
  </section>
  <section className="dashboard-intro-row"><div><div className="eyebrow">YOUR FARM WORKSPACE</div><h2>What would you like to check?</h2><p>Choose a starting point. We'll guide you through each step.</p></div><div className="local-status"><span className="status-dot"/> Prototype mode</div></section>
  <div className="diagnostic-cards">
   <Link to="/crop" className="diagnostic-card crop-diagnostic"><div className="diagnostic-top"><div className="diagnostic-icon"><Leaf size={23}/></div><span className="diagnostic-number">01 / CROP CARE</span></div><div className="diagnostic-card-copy"><h3>Something wrong<br/>with a leaf?</h3><p>Choose from the crop catalogue and add a clear photo to prepare an assessment.</p></div><div className="diagnostic-bottom"><span>Start crop check</span><span className="round-arrow"><ArrowUpRight size={18}/></span></div><div className="crop-art" aria-hidden="true">🌱</div></Link>
   <Link to="/machine" className="diagnostic-card machine-diagnostic"><div className="diagnostic-top"><div className="diagnostic-icon"><AudioWaveform size={23}/></div><span className="diagnostic-number">02 / MACHINE CARE</span></div><div className="diagnostic-card-copy"><h3>Hear something<br/>unusual?</h3><p>Record five seconds of a water pump or small engine sound for an audio check.</p></div><div className="diagnostic-bottom"><span>Start sound check</span><span className="round-arrow"><ArrowUpRight size={18}/></span></div><div className="sound-art" aria-hidden="true"><AudioWaveform size={132}/></div></Link>
  </div>
  <div className="dashboard-lower-grid">
   <section className="activity-panel"><div className="panel-heading"><div><div className="eyebrow">ON THIS DEVICE</div><h3>Your recent activity</h3></div><Link to="/history">View history <ChevronRight size={15}/></Link></div><div className="quick-stats"><div className="quick-stat"><span className="stat-icon leaf-stat"><Leaf size={16}/></span><div><b>{cropCount}</b><small>Crop checks</small></div></div><div className="quick-stat"><span className="stat-icon machine-stat"><AudioWaveform size={16}/></span><div><b>{machineCount}</b><small>Machine checks</small></div></div><div className="quick-stat"><span className="stat-icon total-stat"><Clock3 size={16}/></span><div><b>{history.length}</b><small>Total records</small></div></div></div>
    {recent.length? <div className="recent-list">{recent.map(x=><div className="recent-row" key={x.id}><span className={`recent-icon ${x.domain}`}>{x.domain==='crop'?<Leaf size={17}/>:<AudioWaveform size={17}/>}</span><div className="recent-info"><b>{x.subject}</b><small>{new Date(x.createdAt).toLocaleString()}</small></div><span className="demo-status">Demo record</span></div>)}</div>:<div className="empty-recent"><div className="empty-recent-icon"><Sprout size={22}/></div><div><b>Your farm journey starts here</b><p>When you complete a scan, your activity will appear here.</p></div></div>}
   </section>
   <aside className="trust-panel"><div className="trust-mark"><ShieldCheck size={22}/></div><div className="eyebrow">OUR PROMISE</div><h3>Helpful guidance.<br/><em>Never guesswork.</em></h3><p>When an input is unclear or the model lacks confidence, AcousticAcre should say so and help you reach a human expert.</p><Link to="/help">How it works <ArrowUpRight size={15}/></Link><div className="trust-decoration"><Sprout size={96}/></div></aside>
  </div>
  <section className="voice-strip"><div className="voice-strip-icon"><Volume2 size={21}/></div><div><b>Prefer to listen instead of read?</b><p>Voice-first guidance and reviewed local-language packs are part of the product experience we're building.</p></div><Link to="/help">Explore accessibility <ArrowUpRight size={16}/></Link></section>
  <div className="prototype-disclaimer"><Zap size={16}/><span><b>Prototype transparency:</b> this starter currently demonstrates the user journey. AI models and backend diagnosis are not connected; any generated demo record is not a real diagnosis.</span></div>
 </div>
}
