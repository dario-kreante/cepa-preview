/* Dashboard page */

const PageDashboard = ({ onOpenPatient }) => {
  const k = window.DASHBOARD_KPIS;
  const series = window.SERIE_ATENCIONES;
  const maxA = Math.max(...series.map(s=>s.atenciones));
  const cargas = window.CARGA_PROFESIONAL;
  const maxCarga = Math.max(...cargas.map(c=>c.atenciones));

  const kpis = [
    { label:'Pacientes activos', value: k.pacientesActivos, delta:'+12%', icon:'users', color:'var(--brand-600)', bg:'var(--brand-50)' },
    { label:'Ingresos este mes', value: k.ingresosMes, delta:'+3', icon:'user', color:'var(--info-600)', bg:'var(--info-50)' },
    { label:'Licencias activas', value: k.licenciasActivas, delta:'+8%', icon:'file', color:'var(--warn-600)', bg:'var(--warn-50)' },
    { label:'Controles esta semana', value: k.controlesEstaSemana, delta:'−2', icon:'stethoscope', color:'var(--success-600)', bg:'var(--success-50)', dflat:true },
    { label:'Recetas vigentes', value: k.recetasActivas, delta:'+5', icon:'pill', color:'var(--accent-purple)', bg:'#f4f0ff' },
    { label:'EPT en proceso', value: k.eptEnProceso, delta:'=', icon:'briefcase', color:'var(--accent-teal)', bg:'#ecfdf5', dflat:true },
    { label:'Reintegros en curso', value: k.reintegrosProceso, delta:'+2', icon:'repeat', color:'var(--brand-700)', bg:'var(--brand-50)' },
    { label:'Alertas críticas', value: k.alertasCriticas, delta:'Atención', icon:'alert', color:'var(--danger-600)', bg:'var(--danger-50)', ddown:true },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Dashboard operativo</h1>
          <p>Vista consolidada · 18 de abril de 2026, 10:42</p>
        </div>
        <div className="actions">
          <button className="btn ghost"><Icon name="refresh" size={14}/>Actualizar</button>
          <button className="btn ghost"><Icon name="filter" size={14}/>Período: Abril 2026</button>
          <button className="btn primary"><Icon name="download" size={14}/>Exportar</button>
        </div>
      </div>

      <div className="kpi-grid" style={{marginBottom: 24}}>
        {kpis.map(k => (
          <div key={k.label} className="kpi-tile">
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start'}}>
              <div className="icon-bubble" style={{background:k.bg, color:k.color}}>
                <Icon name={k.icon} size={18}/>
              </div>
              <span className={'delta ' + (k.ddown?'down':k.dflat?'flat':'up')}>
                {!k.dflat && !k.ddown && <Icon name="arrow-up" size={11}/>}
                {k.ddown && <Icon name="arrow-down" size={11}/>}
                {k.delta}
              </span>
            </div>
            <div className="value">{k.value}</div>
            <div className="label">{k.label}</div>
          </div>
        ))}
      </div>

      <div style={{display:'grid', gridTemplateColumns:'2fr 1fr', gap:20, marginBottom:20}}>
        <div className="card">
          <div className="card-header">
            <h3>Atenciones vs. inasistencias · últimos 7 meses</h3>
            <div className="actions">
              <span className="badge-pill info"><span className="dot"/>Atenciones</span>
              <span className="badge-pill danger"><span className="dot"/>Inasistencias</span>
            </div>
          </div>
          <div className="card-body" style={{padding:'20px 24px'}}>
            <svg width="100%" height="220" viewBox="0 0 720 220" preserveAspectRatio="none">
              {[0,0.25,0.5,0.75,1].map(p => (
                <line key={p} x1="40" y1={20+p*170} x2="700" y2={20+p*170} stroke="var(--ink-100)" strokeDasharray="3 3"/>
              ))}
              {[0,0.25,0.5,0.75,1].map(p => (
                <text key={p} x="32" y={24+p*170} textAnchor="end" fontSize="10" fill="var(--ink-400)">
                  {Math.round(maxA*(1-p))}
                </text>
              ))}
              {series.map((s,i) => {
                const x = 60 + i*(640/(series.length-1));
                const y = 20 + (1 - s.atenciones/maxA)*170;
                const yI = 20 + (1 - s.inasistencias/maxA)*170;
                const nx = i<series.length-1 ? 60 + (i+1)*(640/(series.length-1)) : x;
                const ny = i<series.length-1 ? 20 + (1 - series[i+1].atenciones/maxA)*170 : y;
                const nyI = i<series.length-1 ? 20 + (1 - series[i+1].inasistencias/maxA)*170 : yI;
                return (
                  <g key={i}>
                    {i<series.length-1 && <line x1={x} y1={y} x2={nx} y2={ny} stroke="var(--brand-600)" strokeWidth="2"/>}
                    {i<series.length-1 && <line x1={x} y1={yI} x2={nx} y2={nyI} stroke="var(--danger-500)" strokeWidth="2" strokeDasharray="4 3"/>}
                    <circle cx={x} cy={y} r="4" fill="#fff" stroke="var(--brand-600)" strokeWidth="2"/>
                    <circle cx={x} cy={yI} r="3" fill="var(--danger-500)"/>
                    <text x={x} y="212" textAnchor="middle" fontSize="10" fill="var(--ink-500)">{s.mes}</text>
                    <text x={x} y={y-8} textAnchor="middle" fontSize="10" fontWeight="700" fill="var(--brand-700)">{s.atenciones}</text>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Tareas del día</h3>
            <span className="badge-pill warn"><span className="dot"/>7 pendientes</span>
          </div>
          <div className="card-body" style={{padding:0}}>
            {[
              {t:'Revisar LM-10003 (vence mañana)', p:PATIENTS[0], urg:'danger'},
              {t:'Confirmar control de las 15:30', p:PATIENTS[6], urg:'warn'},
              {t:'Gestionar receta farmacia Socorro', p:PATIENTS[13], urg:'warn'},
              {t:'Enviar informe EPT pendiente', p:PATIENTS[3], urg:'danger'},
              {t:'Agendar primera acogida', p:PATIENTS[9], urg:'info'},
            ].map((t,i) => (
              <div key={i} style={{padding:'12px 18px', borderBottom: i<4?'1px solid var(--ink-100)':'none', display:'flex', gap:10, alignItems:'flex-start'}}>
                <input type="checkbox" style={{marginTop:3}}/>
                <div style={{flex:1}}>
                  <div style={{fontSize:12.5, color:'var(--ink-900)', fontWeight:500, lineHeight:1.35}}>{t.t}</div>
                  <div style={{fontSize:11, color:'var(--ink-500)', marginTop:3}}>{t.p.nombre} · Folio {t.p.folio}</div>
                </div>
                <span className={'badge-pill ' + t.urg} style={{fontSize:10}}>{t.urg==='danger'?'Urgente':t.urg==='warn'?'Hoy':'Pronto'}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:20}}>
        <div className="card">
          <div className="card-header">
            <h3>Carga por profesional</h3>
            <button className="btn ghost sm">Ver reporte completo</button>
          </div>
          <div className="card-body" style={{padding:'6px 0'}}>
            {cargas.map(c => (
              <div key={c.nombre} style={{padding:'10px 20px', display:'grid', gridTemplateColumns:'160px 1fr 60px', gap:12, alignItems:'center'}}>
                <div>
                  <div style={{fontSize:12.5, fontWeight:600, color:'var(--ink-900)'}}>{c.nombre}</div>
                  <div style={{fontSize:11, color:'var(--ink-500)'}}>{c.casos} casos activos</div>
                </div>
                <div style={{background:'var(--ink-100)', height:8, borderRadius:4, overflow:'hidden'}}>
                  <div style={{width: (c.atenciones/maxCarga*100)+'%', height:'100%', background:'linear-gradient(90deg, var(--brand-500), var(--brand-600))', borderRadius:4}}/>
                </div>
                <div style={{textAlign:'right', fontSize:13, fontWeight:700, color:'var(--ink-900)'}}>{c.atenciones}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Últimos ingresos</h3>
            <button className="btn ghost sm" onClick={()=>onOpenPatient && onOpenPatient(null)}>Ver todos</button>
          </div>
          <div className="card-body" style={{padding:0}}>
            <table className="data-table">
              <thead>
                <tr><th>Folio</th><th>Paciente</th><th>Derivación</th><th>Estado</th></tr>
              </thead>
              <tbody>
                {PATIENTS.slice(0,6).map(p => (
                  <tr key={p.folio} onClick={()=>onOpenPatient(p)}>
                    <td className="mono">{p.folio}</td>
                    <td><div style={{fontWeight:600}}>{p.nombre}</div><div style={{fontSize:11, color:'var(--ink-500)'}}>{p.rut}</div></td>
                    <td style={{fontSize:12}}>{p.tipoDerivacion}</td>
                    <td><span className={'badge-pill ' + (p.estado==='Activo'?'success':p.estado==='Pendiente'?'warn':p.estado==='Cerrado'?'neutral':'info')}>{p.estado}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

window.PageDashboard = PageDashboard;
