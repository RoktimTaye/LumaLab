import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import { ArrowDown, ArrowRight, ArrowUpRight, Check, CheckCheck, ChevronRight, Download, Image, Layers, Maximize2, ScanLine, ShieldCheck, SlidersHorizontal, Sparkles, Sun, Upload } from 'lucide-react'
import { Header } from '../components/Header'
import { Brand } from '../components/Brand'
import { PhotoPreview } from '../components/PhotoPreview'
import { PRESETS } from '../lib/editor'
import styles from './Home.module.css'

const features = [
  { icon: SlidersHorizontal, label: '01 / MAKE IT YOURS', title: 'Small adjustments.\nA different perspective.', copy: 'Bring out what caught your eye. Fine-tune the light, find your colours, and give every detail a little more intention.', items: ['Brightness, contrast & saturation', 'Warmth, sharpness & vignette', 'Your original, always preserved'], image: '/images/forest.jpg', kind: 'controls' },
  { icon: Layers, label: '02 / FIND YOUR FEELING', title: 'One photograph.\nFive ways to see it.', copy: 'From the warmth of a late afternoon to the quiet of black and white. Find a starting point, then make it your own.', items: ['Five thoughtfully balanced presets', 'Switch looks without starting over', 'Refine every preset with manual controls'], image: '/images/alpine.jpg', kind: 'presets' },
  { icon: Sparkles, label: '03 / A LITTLE ASSISTANCE', title: 'Good light.\nLess guesswork.', copy: 'Automatic Enhancement is designed to balance light and colour using image analysis. A thoughtful first step, with you in control of the final look.', items: ['Brightness and contrast balancing', 'Natural colour and warmth adjustments', 'Available when the editing service is connected'], image: '/images/nature.jpg', kind: 'enhance' },
  { icon: ScanLine, label: '04 / SEE THE DIFFERENCE', title: 'Keep the moment.\nPerfect the feeling.', copy: 'Compare the starting point with your own perspective. See exactly what changed, without losing a single adjustment.', items: ['Interactive before-and-after comparison', 'Non-destructive editing from the original', 'Full-resolution JPEG export after backend setup'], image: '/images/forest.jpg', kind: 'compare' },
]

function SectionIntro({ label, title, copy }: { label: string; title: string; copy: string }) {
  return <div className={styles.sectionIntro}><span className="eyebrow">{label}</span><h2>{title}</h2><p>{copy}</p></div>
}

export function Home() {
  const [preset, setPreset] = useState(1)
  const [compare, setCompare] = useState(true)
  const [split, setSplit] = useState(48)
  return <>
    {/* <div className={styles.announcement}><span className="status-dot" /> A little light. A whole new perspective. <span className={styles.announcementDivider}>/</span><Link to="/studio">Meet your new studio <ArrowRight size={12} /></Link></div> */}
    <Header />
    <main id="main">
      <section className={`container ${styles.hero}`}>
        <div className={styles.heroTop}><div className={styles.heroCopy}>
          <div className={styles.heroEyebrow}><span className="status-dot" /><span className="eyebrow">A NEW PERSPECTIVE ON PHOTO EDITING</span></div>
          <h1>Light. Colour.<br /><span>Create.</span></h1>
          <p>The moment is yours. Make the photograph feel like it.<br className={styles.desktopBreak} /> Simple tools, thoughtful presets, and room to explore.</p>
          <div className={styles.heroActions}><Link to="/studio" className="button primary">Start Editing <ArrowUpRight size={17} /></Link></div>
          <div className={styles.heroNote}><Check size={13} /> No account needed <span>·</span> Free to create</div>
        </div>
        <div className={styles.heroAside} aria-hidden="true"><div className={styles.lightRings}><div /><div /><div /><span>luma / light</span></div><div className={styles.colorSpectrum}><i /><i /><i /><i /></div><div className={styles.asideMeta}><span>RGBW COLOUR SYSTEM</span><span>01 — ∞</span></div></div></div>
        <div className={styles.heroConsole}>
          <div className={styles.consoleToolbar}><span className={styles.consoleTitle}><span className={styles.windowDots}><i /><i /><i /></span> LUMALAB / STUDIO PREVIEW</span><span className={styles.consoleStatus}><span className="status-dot" /> A new point of view</span></div>
          <div className={styles.demoBody}>
            <div className={styles.demoSidebar}><span className="eyebrow">YOUR CREATIVE TOOLKIT</span><div className={styles.toolActive}><SlidersHorizontal size={16} /> Adjustments</div><div><Layers size={16} /> Preset library <span>05</span></div><div><ScanLine size={16} /> Before & after</div><div className={styles.demoHint}><span className="status-dot" /> TRY A LOOK BELOW<small>One original.<br />Endless perspective.</small></div></div>
            <div className={styles.demoPhoto}><PhotoPreview src="/images/alpine.jpg" name="Sunlit alpine mountain, interactive editing preview" values={PRESETS[preset].values} compare={compare} split={split} onSplit={setSplit} eager /><div className={styles.photoToolbar}><span><Image size={13} /> alpine-perspective.jpg</span><button aria-pressed={compare} onClick={() => setCompare(!compare)}><ScanLine size={14} /> {compare ? 'Hide comparison' : 'Compare original'}</button><Link to="/studio" aria-label="Open full studio"><Maximize2 size={14} /></Link></div></div>
            <div className={styles.demoAdjust}><span>LIGHT & COLOUR <Sun size={14} /></span>{[['Brightness', PRESETS[preset].values.brightness], ['Contrast', PRESETS[preset].values.contrast], ['Saturation', PRESETS[preset].values.saturation]].map(([name, value]) => <div className={styles.miniControl} key={name}><div>{name}<span>{value}</span></div><i><b style={{ left: `${Number(value) / 2}%` }} /></i></div>)}<div className={styles.activeLook}><Layers size={14} /><span>ACTIVE LOOK<strong>{PRESETS[preset].name}</strong></span><Check size={14} /></div><span className={styles.previewCaption}>Interactive frontend preview</span></div>
          </div>
          <div className={styles.presetBar}><span>FIND YOUR LOOK</span><div>{PRESETS.map((item, index) => <button key={item.name} className={preset === index ? styles.selectedPreset : ''} aria-pressed={preset === index} onClick={() => setPreset(index)}>{preset === index && <span className="status-dot" />}{item.name}</button>)}</div><span className={styles.presetCount}>05 PRESETS</span></div>
        </div>
        <div className={styles.heroFoot}><span>MADE FOR THE MOMENTS WORTH KEEPING</span><div><span><ShieldCheck size={14} /> Original preserved</span><span><SlidersHorizontal size={14} /> Creative control</span><span><CheckCheck size={14} /> No subscriptions</span></div></div>
      </section>

      <section className={`container ${styles.section}`} id="about">
        <SectionIntro label="LESS FRICTION. MORE CREATION." title="Everything you need. Space to create." copy="A focused workspace for your photographs. No complicated toolbars. No steep learning curve. Just the essentials, beautifully connected." />
        <div className={styles.identityCards}>{[
          { icon: Sun, title: 'Chase the light', copy: 'Recover the feeling of a moment with intuitive light and colour adjustments.', number: '01' },
          { icon: Layers, title: 'Find your signature', copy: 'Start with a considered preset. Refine the details until it feels like you.', number: '02' },
          { icon: ShieldCheck, title: 'Create with confidence', copy: 'Explore freely. Your original stays untouched, and a fresh start is one click away.', number: '03' },
        ].map(item => <article key={item.title}><div><item.icon size={21} /><span>{item.number}</span></div><h3>{item.title}</h3><p>{item.copy}</p></article>)}</div>
        <div className={styles.specStrip}><span>ONE FOCUSED WORKSPACE</span><div><strong>06</strong> Essential controls</div><div><strong>05</strong> Creative presets</div><div><strong>01</strong> Original. Always yours.</div></div>
      </section>

      <section className={styles.pipelineSection}><div className="container"><SectionIntro label="BUILT AROUND YOUR ORIGINAL" title="Your vision, layer by layer." copy="Every adjustment starts with the same original photograph. Explore a new direction without losing where you began." />
        <div className={styles.pipeline}><div className={styles.pipelineNote}><span className="eyebrow">01 / PRESERVE</span><h3>One untouched original.</h3><p>Your starting point stays intact.<br />Reset whenever inspiration changes.</p></div>
          <svg className={styles.stack} viewBox="0 0 440 420" role="img" aria-label="Editing stages: original photograph, light, colour, detail, and final preview"><defs><linearGradient id="mintPlate" x2="1" y2="1"><stop stopColor="#94f7bc" stopOpacity=".72"/><stop offset="1" stopColor="#246c5a" stopOpacity=".2"/></linearGradient><linearGradient id="bluePlate" x2="1" y2="1"><stop stopColor="#8fafff" stopOpacity=".6"/><stop offset="1" stopColor="#24385b" stopOpacity=".2"/></linearGradient></defs><g stroke="#53625d" strokeDasharray="3 5" opacity=".45"><path d="M50 100v220M390 100v220M220 20v370" /></g>{[4,3,2,1,0].map((n) => <g key={n} transform={`translate(0 ${n * 54})`}><path d="M220 20 390 100 220 180 50 100Z" fill={n === 0 ? '#111a17' : n % 2 ? 'url(#bluePlate)' : 'url(#mintPlate)'} stroke={n % 2 ? '#8fafff' : '#94f7bc'} strokeOpacity=".55"/><path d="m50 100 170 80 170-80v7l-170 80-170-80z" fill={n % 2 ? '#8fafff' : '#94f7bc'} opacity=".12" /></g>)}<g transform="translate(200 80)" fill="none" stroke="#94f7bc" strokeWidth="1.5"><path d="m20-6 27 13-27 13L-7 7zM-7 15l27 13 27-13M-7 23l27 13 27-13"/></g></svg>
          <div className={styles.pipelineNote}><span className="eyebrow">02 / REIMAGINE</span><h3>A little more you.</h3><p>Light → colour → detail.<br />One complete, considered look.</p><Link to="/studio" className={styles.textLink}>Find your perspective <ArrowUpRight size={15} /></Link></div>
        </div></div></section>

      <section className={`container ${styles.features}`} id="features"><SectionIntro label="YOUR TOOLS. YOUR PERSPECTIVE." title="Make room for the remarkable." copy="Everything has a purpose. Every control is yours." />
        {features.map((feature, index) => <article className={`${styles.featureRow} ${index % 2 ? styles.reverse : ''}`} key={feature.title}>
          <div className={styles.featureCopy}><feature.icon size={24} /><span className="eyebrow">{feature.label}</span><h3>{feature.title.split('\n').map((line, i) => <span key={line}>{i > 0 && <br />}{line}</span>)}</h3><p>{feature.copy}</p><ul>{feature.items.map(item => <li key={item}><Check size={14} />{item}</li>)}</ul><Link to="/studio" className={styles.textLink}>Explore in the studio <ArrowUpRight size={15} /></Link></div>
          <div className={styles.featureMedia} style={{ backgroundImage: `linear-gradient(0deg,#090a0d66,#090a0d22),url(${feature.image})` }}>
            <div className={styles.featureConsole}><div className={styles.featureConsoleHeader}><feature.icon size={14} /><span>{['ADJUST YOUR PERSPECTIVE','THE PRESET LIBRARY','AUTOMATIC ENHANCEMENT','A NEW POINT OF VIEW'][index]}</span><span className="status-dot" /></div>
              {feature.kind === 'controls' && <div className={styles.visualControls}>{[['Brightness','112','56%'],['Contrast','108','54%'],['Saturation','118','59%'],['Warmth','+16','66%']].map(([label,value,position]) => <div className={styles.miniControl} key={label}><div>{label}<span>{value}</span></div><i><b style={{left:position}}/></i></div>)}<span className={styles.consoleFoot}><Check size={12} /> A preview of your creative controls</span></div>}
              {feature.kind === 'presets' && <div className={styles.visualPresets}>{PRESETS.slice(1).map(item => <div key={item.name}><img src="/images/alpine.jpg" alt="" loading="lazy" width="150" height="100" style={{filter:`saturate(${item.values.saturation / 100}) sepia(${item.values.warmth > 0 ? .45 : 0})`}}/><span>{item.name}</span></div>)}</div>}
              {feature.kind === 'enhance' && <div className={styles.enhanceVisual}><div><Sparkles size={28}/></div><h4>A balanced starting point.</h4><p>Light, contrast and colour.<br/>Working together.</p><span>COMING WITH THE EDITING SERVICE</span></div>}
              {feature.kind === 'compare' && <div className={styles.comparisonVisual}><PhotoPreview src="/images/forest.jpg" name="Forest before and after a Golden Hour preset" values={PRESETS[2].values} compare split={50}/><span>Original preserved. Creativity unlocked.</span></div>}
            </div><span className={styles.mediaCaption}>LUMALAB / INTERFACE PREVIEW</span>
          </div>
        </article>)}
      </section>

      <section className={styles.workflowSection} id="workflow"><div className="container"><SectionIntro label="FROM FIRST FRAME TO FINAL FEELING" title="A simple path to your next favourite." copy="Less time learning the tools. More time seeing what’s possible." /><ol className={styles.workflow}>{[
        {icon:Upload,title:'Bring your photograph',copy:'Choose a still JPG, PNG or WebP. One moment is all it takes.'},
        {icon:SlidersHorizontal,title:'Make it your own',copy:'Choose a preset, then find the right balance with six simple controls.'},
        {icon:ScanLine,title:'See the difference',copy:'Compare with the original. Refine the details. Trust your eye.'},
        {icon:Download,title:'Take it with you',copy:'Full-resolution JPEG export will be available with the backend.'},
      ].map((step,i)=><li key={step.title}><div><span>0{i+1}</span><step.icon size={18}/></div><h3>{step.title}</h3><p>{step.copy}</p></li>)}</ol><div className={styles.formatNote}><Image size={15}/><span>JPG, PNG & WebP <i>·</i> Up to 10 MB <i>·</i> Up to 24 megapixels</span></div></div></section>

      <section className={`container ${styles.closing}`}><span className="eyebrow">SOMETHING GOOD IS ALREADY IN YOUR FRAME</span><h2>Bring it to light.</h2><p>Your next favourite photograph is waiting to happen.</p><Link to="/studio" className="button primary">Start Editing <ArrowUpRight size={17}/></Link><span className={styles.closingNote}>NO SIGN-UP. JUST YOUR PERSPECTIVE.</span></section>
    </main>
    <footer className={styles.footer}><div className={`container ${styles.footerTop}`}><div><Brand/><p>A little light. A little colour.<br/>Something entirely yours.</p></div><div><span>EXPLORE</span><Link to="/studio">Editing Studio <ArrowUpRight size={12}/></Link><a href="#features">Features</a><a href="#about">About LumaLab</a></div><div><span>THE WORKSPACE</span><Link to="/studio">Manual adjustments</Link><Link to="/studio">Preset library</Link><a href="#workflow">How it works</a></div><div className={styles.footerStatus}><span className="status-dot"/><span>FRONTEND PREVIEW</span><p>Built for a clearer perspective.<br/>Backend integration comes next.</p></div></div><div className={`container ${styles.footerBottom}`}><span>© {new Date().getFullYear()} LumaLab. Light. Colour. Create.</span><span>MADE FOR THE WAY YOU SEE <ChevronRight size={12}/></span></div></footer>
  </>
}
