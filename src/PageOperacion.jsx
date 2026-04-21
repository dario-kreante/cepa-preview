/* Agendamiento + Reportería */

const PageAgenda = () => {
  const { profesionales, slots } = window.AGENDA_SLOTS;
  const horas = ['08:30','09:30','10:30','11:30','12:30','14:30','15:30','16:30','17:30'];
  const dias = ['L 14','M 15','X 16','J 17','V 18','L 21','M 22'];
  const [diaSel, setDiaSel] = React.useState(4); // Viernes 18

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Agendamiento</h1>
          <p>Agenda multi-profesional · Viernes 18 de abril de 2026</p>
        </div>
        <div className="actions">
          <button className="btn ghost"><Icon name="calendar" size={14}/>Vista semanal</button>
          <button className="btn ghost"><Icon name="download" size={14}/>Exportar iCal</button>
          <button className="btn primary"><Icon name="plus" size={14}/>Nueva cita</button>
        </div>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'1fr 280px', gap:20}}>
        <div className="card">
          <div className="card-header">
            <h3>Agenda del día</h3>
            <div style={{display:'flex', gap:4}}>
              {dias.map((d,i) => (
                <button key={d} onClick={()=>setDiaSel(i)}
                  className={'btn ' + (i===diaSel?'primary':'ghost') + ' sm'} style={{minWidth:48}}>{d}</button>
              ))}
            </div>
          </div>
          <div className="card-body" style={{padding:0, overflow:'auto'}}>
            <div style={{display:'grid', gridTemplateColumns:'70px repeat('+profesionales.length+', 1fr)', minWidth:900}}>
              <div style={{padding:'10px 8px', borderBottom:'1px solid var(--ink-100)', background:'var(--ink-50)'}}></div>
              {profesionales.map(p => (
                <div key={p.key} style={{padding:'10px 8px', borderBottom:'1px solid var(--ink-100)', background:'var(--ink-50)', borderLeft:'1px solid var(--ink-100)', textAlign:'center'}}>
                  <div style={{width:10, height:10, borderRadius:3, background:p.color, display:'inline-block', marginRight:6, verticalAlign:'middle'}}/>
                  <span style={{fontSize:11, fontWeight:600, color:'var(--ink-700)'}}>{p.nombre.split(' ').slice(0,2).join(' ')}</span>
                </div>
              ))}
              {horas.map(h => (
                <React.Fragment key={h}>
                  <div style={{padding:'6px 8px', borderBottom:'1px solid var(--ink-100)', fontSize:11, color:'var(--ink-500)', fontWeight:600, textAlign:'right', background:'var(--ink-50)'}}>{h}</div>
                  {profesionales.map(p => {
                    const slot = slots.find(s => s.profesional === p.key && s.hora === h);
                    return (
                      <div key={p.key+h} style={{padding:4, borderBottom:'1px solid var(--ink-100)', borderLeft:'1px solid var(--ink-100)', minHeight:56}}>
                        {slot && (
                          <div style={{background:p.color+'15', borderLeft:'3px solid '+p.color, padding:'6px 8px', borderRadius:4, cursor:'pointer'}}>
                            <div style={{fontSize:11.5, fontWeight:600, color:'var(--ink-900)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{slot.paciente.split(' ').slice(0,2).join(' ')}</div>
                            <div style={{fontSize:10, color:'var(--ink-500)', marginTop:2}}>{slot.tipo}</div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>

        <div style={{display:'flex', flexDirection:'column', gap:16}}>
          <div className="card">
            <div className="card-header"><h3>Resumen del día</h3></div>
            <div className="card-body">
              <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:10}}>
                <div style={{padding:10, background:'var(--brand-50)', borderRadius:6, textAlign:'center'}}>
                  <div style={{fontSize:20, fontWeight:700, color:'var(--brand-700)'}}>{slots.length}</div>
                  <div style={{fontSize:11, color:'var(--brand-700)'}}>Citas agendadas</div>
                </div>
                <div style={{padding:10, background:'var(--success-50)', borderRadius:6, textAlign:'center'}}>
                  <div style={{fontSize:20, fontWeight:700, color:'var(--success-700)'}}>{slots.filter(s=>s.estado==='Confirmada').length}</div>
                  <div style={{fontSize:11, color:'var(--success-700)'}}>Confirmadas</div>
                </div>
                <div style={{padding:10, background:'var(--warn-50)', borderRadius:6, textAlign:'center'}}>
                  <div style={{fontSize:20, fontWeight:700, color:'var(--warn-700)'}}>{slots.filter(s=>s.estado==='En espera').length}</div>
                  <div style={{fontSize:11, color:'var(--warn-700)'}}>En espera</div>
                </div>
                <div style={{padding:10, background:'var(--ink-100)', borderRadius:6, textAlign:'center'}}>
                  <div style={{fontSize:20, fontWeight:700, color:'var(--ink-700)'}}>{54 - slots.length}</div>
                  <div style={{fontSize:11, color:'var(--ink-700)'}}>Slots libres</div>
                </div>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="card-header"><h3>Profesionales</h3></div>
            <div className="card-body" style={{padding:0}}>
              {profesionales.map(p => {
                const pSlots = slots.filter(s=>s.profesional===p.key);
                return (
                  <div key={p.key} style={{padding:'10px 18px', borderBottom:'1px solid var(--ink-100)', display:'flex', alignItems:'center', gap:10}}>
                    <div style={{width:10, height:10, borderRadius:3, background:p.color}}/>
                    <div style={{flex:1}}>
                      <div style={{fontSize:12.5, fontWeight:600}}>{p.nombre}</div>
                      <div style={{fontSize:11, color:'var(--ink-500)'}}>{pSlots.length}/9 citas</div>
                    </div>
                    <div style={{fontSize:11, fontWeight:600, color:p.color}}>{Math.round(pSlots.length/9*100)}%</div>
                  </div>
                );
              })}
            </div>
          </div>
          <div className="card">
            <div className="card-header"><h3>Próximo disponible</h3></div>
            <div className="card-body">
              <div style={{fontSize:12}}>
                <div style={{padding:'8px 0', borderBottom:'1px solid var(--ink-100)'}}><b>Dr. Álvaro Soto</b><br/><span style={{color:'var(--ink-500)', fontSize:11}}>Lun 21, 09:30</span></div>
                <div style={{padding:'8px 0', borderBottom:'1px solid var(--ink-100)'}}><b>Ps. Camila Díaz</b><br/><span style={{color:'var(--ink-500)', fontSize:11}}>Hoy, 17:30</span></div>
                <div style={{padding:'8px 0'}}><b>Ps. Javiera Pinto</b><br/><span style={{color:'var(--ink-500)', fontSize:11}}>Lun 21, 08:30</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const PageReportes = () => {
  const sI = window.SERIE_INGRESOS;
  const maxI = Math.max(...sI.map(s=>s.value));
  const cargas = window.CARGA_PROFESIONAL;

  const distDerivacion = window.TIPOS_DERIVACION.map(t => ({
    tipo: t, count: PATIENTS.filter(p=>p.tipoDerivacion===t).length
  })).filter(x => x.count > 0).sort((a,b)=>b.count-a.count);
  const distDX = [
    {t:'Trast. adaptativo', n: 8, c:'var(--brand-600)'},
    {t:'Depresión', n: 6, c:'var(--accent-purple)'},
    {t:'Ansiedad generalizada', n: 5, c:'var(--info-600)'},
    {t:'Burnout', n: 3, c:'var(--warn-600)'},
    {t:'TEPT', n: 2, c:'var(--danger-600)'},
    {t:'Otros', n: 1, c:'var(--ink-400)'},
  ];
  const totDX = distDX.reduce((s,x)=>s+x.n,0);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Reportería</h1>
          <p>Indicadores operativos, tendencias y reportes ISL</p>
        </div>
        <div className="actions">
          <button className="btn ghost"><Icon name="filter" size={14}/>Período: últimos 6 meses</button>
          <button className="btn ghost"><Icon name="share" size={14}/>Compartir</button>
          <button className="btn primary"><Icon name="download" size={14}/>Exportar PDF</button>
        </div>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'2fr 1fr', gap:20, marginBottom:20}}>
        <div className="card">
          <div className="card-header"><h3>Ingresos mensuales</h3><button className="btn ghost sm">Ver detalle</button></div>
          <div className="card-body" style={{padding:'20px 24px'}}>
            <svg width="100%" height="200" viewBox="0 0 720 200" preserveAspectRatio="none">
              {[0,0.5,1].map(p => <line key={p} x1="40" y1={20+p*150} x2="700" y2={20+p*150} stroke="var(--ink-100)"/>)}
              {sI.map((s,i) => {
                const x = 60 + i * (640/(sI.length-1));
                const h = (s.value/maxI)*150;
                return (
                  <g key={i}>
                    <rect x={x-22} y={170-h} width="44" height={h} rx="3" fill="url(#grad1)"/>
                    <text x={x} y="190" textAnchor="middle" fontSize="10" fill="var(--ink-500)">{s.mes}</text>
                    <text x={x} y={165-h} textAnchor="middle" fontSize="11" fontWeight="700" fill="var(--brand-700)">{s.value}</text>
                  </g>
                );
              })}
              <defs>
                <linearGradient id="grad1" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--brand-500)"/>
                  <stop offset="100%" stopColor="var(--brand-700)"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
        </div>
        <div className="card">
          <div className="card-header"><h3>Distribución diagnósticos</h3></div>
          <div className="card-body">
            <svg width="180" height="180" viewBox="0 0 180 180" style={{display:'block', margin:'0 auto 16px'}}>
              {(() => {
                let acc = 0;
                return distDX.map((d,i) => {
                  const a0 = (acc/totDX) * Math.PI * 2 - Math.PI/2;
                  acc += d.n;
                  const a1 = (acc/totDX) * Math.PI * 2 - Math.PI/2;
                  const r = 72, cx = 90, cy = 90;
                  const x0 = cx + Math.cos(a0)*r, y0 = cy + Math.sin(a0)*r;
                  const x1 = cx + Math.cos(a1)*r, y1 = cy + Math.sin(a1)*r;
                  const large = a1 - a0 > Math.PI ? 1 : 0;
                  return <path key={i} d={`M ${cx} ${cy} L ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1} Z`} fill={d.c}/>;
                });
              })()}
              <circle cx="90" cy="90" r="40" fill="#fff"/>
              <text x="90" y="88" textAnchor="middle" fontSize="22" fontWeight="700" fill="var(--ink-900)">{totDX}</text>
              <text x="90" y="104" textAnchor="middle" fontSize="10" fill="var(--ink-500)">casos</text>
            </svg>
            <div style={{display:'flex', flexDirection:'column', gap:6}}>
              {distDX.map((d,i) => (
                <div key={i} style={{display:'flex', alignItems:'center', gap:8, fontSize:12}}>
                  <div style={{width:10, height:10, background:d.c, borderRadius:2}}/>
                  <span style={{flex:1}}>{d.t}</span>
                  <span className="mono" style={{fontWeight:600}}>{d.n}</span>
                  <span className="mono" style={{color:'var(--ink-500)', minWidth:34, textAlign:'right'}}>{Math.round(d.n/totDX*100)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:20}}>
        <div className="card">
          <div className="card-header"><h3>Tipo de derivación</h3></div>
          <div className="card-body">
            {distDerivacion.map(d => (
              <div key={d.tipo} style={{marginBottom:10}}>
                <div style={{display:'flex', justifyContent:'space-between', fontSize:12.5, marginBottom:4}}>
                  <b>{d.tipo}</b><span className="mono">{d.count}</span>
                </div>
                <div style={{background:'var(--ink-100)', height:6, borderRadius:3}}>
                  <div style={{width:(d.count/PATIENTS.length*100)+'%', height:'100%', background:'var(--brand-600)', borderRadius:3}}/>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="card">
          <div className="card-header"><h3>KPIs operativos</h3></div>
          <div className="card-body">
            <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:10}}>
              {[
                {t:'Tasa de cierre', v:'68%', sub:'+4 pts vs. trim. ant.', c:'var(--success-700)', bg:'var(--success-50)'},
                {t:'Inasistencia promedio', v:'11.2%', sub:'dentro de rango', c:'var(--ink-700)', bg:'var(--ink-100)'},
                {t:'Tiempo medio tratamiento', v:'84 días', sub:'meta: 90 días', c:'var(--info-700)', bg:'var(--info-50)'},
                {t:'Satisfacción (CSAT)', v:'4.6/5', sub:'n=42 encuestas', c:'var(--success-700)', bg:'var(--success-50)'},
                {t:'Derivación oportuna', v:'92%', sub:'dentro de plazo ISL', c:'var(--brand-700)', bg:'var(--brand-50)'},
                {t:'RECA promedio', v:'37 días', sub:'desde solicitud', c:'var(--warn-700)', bg:'var(--warn-50)'},
              ].map(k=>(
                <div key={k.t} style={{padding:12, background:k.bg, borderRadius:8}}>
                  <div style={{fontSize:11, color:k.c, fontWeight:600, textTransform:'uppercase', letterSpacing:'0.04em'}}>{k.t}</div>
                  <div style={{fontSize:22, fontWeight:700, color:k.c, marginTop:4}}>{k.v}</div>
                  <div style={{fontSize:11, color:k.c, marginTop:2, opacity:0.8}}>{k.sub}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

window.PageAgenda = PageAgenda;
window.PageReportes = PageReportes;
