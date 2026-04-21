/* Ingresos + Ficha 360° del paciente */

const StatusBadge = ({ state }) => {
  const m = {
    'Activo':'success', 'En tratamiento':'info', 'Pendiente':'warn',
    'Cerrado':'neutral', 'Derivado':'purple',
    'Realizada':'success', 'Enviado':'success', 'OK':'success', 'Respondida':'success',
    'No':'neutral', 'EP':'info', 'EC':'purple',
  };
  return <span className={'badge-pill ' + (m[state]||'neutral')}>{state}</span>;
};
window.StatusBadge = StatusBadge;

const PatientSheet = ({ patient, onClose }) => {
  const [tab, setTab] = React.useState('resumen');
  if (!patient) return null;
  const lic = window.LICENCIAS.filter(l => l.folio === patient.folio);
  const rec = window.RECETAS.filter(r => r.folio === patient.folio);
  const totalDiasLic = lic.reduce((s,l)=>s+l.dias, 0);

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose}/>
      <div className="drawer">
        <div className="drawer-header">
          <div className="avatar" style={{background:'var(--brand-500)', width:42, height:42, fontSize:14}}>{patient.inicial}</div>
          <div>
            <h2>{patient.nombre}</h2>
            <div className="sub">Folio {patient.folio} · {patient.rut} · {patient.region}</div>
          </div>
          <button className="icon-btn close" onClick={onClose}><Icon name="close" size={18}/></button>
        </div>

        <div style={{padding:'0 22px', background:'var(--brand-800)', borderBottom:'1px solid var(--brand-900)'}}>
          <div style={{display:'flex', gap:0}}>
            {['resumen','licencias','farmacos','controles','observaciones'].map(t => (
              <button key={t} onClick={()=>setTab(t)}
                style={{
                  padding:'12px 16px', fontSize:12.5, fontWeight:600,
                  color: tab===t ? '#fff' : 'rgba(255,255,255,0.6)',
                  borderBottom: '2px solid ' + (tab===t?'#fff':'transparent'),
                  textTransform:'capitalize'
                }}>
                {t === 'farmacos' ? 'Fármacos' : t}
              </button>
            ))}
          </div>
        </div>

        <div className="drawer-body">
          {tab === 'resumen' && (
            <div style={{display:'flex', flexDirection:'column', gap:16}}>
              <div className="card">
                <div className="card-header"><h3>Datos personales</h3></div>
                <div className="card-body">
                  <div className="info-grid">
                    <div className="info-row"><span className="label">RUT</span><span className="value mono">{patient.rut}</span></div>
                    <div className="info-row"><span className="label">Teléfono</span><span className="value">{patient.telefono}</span></div>
                    <div className="info-row"><span className="label">Correo</span><span className="value">{patient.correo}</span></div>
                    <div className="info-row"><span className="label">Región</span><span className="value">{patient.region}</span></div>
                    <div className="info-row"><span className="label">Comuna</span><span className="value">{patient.comuna}</span></div>
                    <div className="info-row"><span className="label">Tipo de derivación</span><span className="value">{patient.tipoDerivacion}</span></div>
                  </div>
                </div>
              </div>

              <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:16}}>
                <div className="card">
                  <div className="card-header"><h3>Fechas clave</h3></div>
                  <div className="card-body">
                    <div className="info-grid" style={{gridTemplateColumns:'1fr 1fr'}}>
                      <div className="info-row"><span className="label">Ingreso</span><span className="value">{fmtDate(patient.fechaIngreso)}</span></div>
                      <div className="info-row"><span className="label">DIEP/DIAT</span><span className="value">{fmtDate(patient.fechaDIEP)}</span></div>
                      <div className="info-row"><span className="label">Primera acogida</span><span className="value">{fmtDate(patient.fechaAcogida)}</span></div>
                      <div className="info-row"><span className="label">Próximo control</span><span className="value">{fmtDate(patient.proxControl)}</span></div>
                    </div>
                  </div>
                </div>
                <div className="card">
                  <div className="card-header"><h3>Estado del caso</h3></div>
                  <div className="card-body">
                    <div className="info-grid" style={{gridTemplateColumns:'1fr 1fr'}}>
                      <div className="info-row"><span className="label">Estado</span><span><StatusBadge state={patient.estado}/></span></div>
                      <div className="info-row"><span className="label">Tipo alta</span><span className="value">{patient.tipoAlta}</span></div>
                      <div className="info-row"><span className="label">RECA</span><span className="value"><StatusBadge state={patient.recaTipo}/> {patient.recaNumero}</span></div>
                      <div className="info-row"><span className="label">Obstaculización</span><span className="value">{patient.obstaculizacion?'Sí':'No'}</span></div>
                    </div>
                  </div>
                </div>
              </div>

              <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:16}}>
                <div className="card">
                  <div className="card-header"><h3>Área médica</h3></div>
                  <div className="card-body">
                    <div className="info-grid" style={{gridTemplateColumns:'1fr'}}>
                      <div className="info-row"><span className="label">Evaluación médica</span><span><StatusBadge state={patient.evaluacionMedica}/></span></div>
                      <div className="info-row"><span className="label">Médico tratante</span><span className="value">{patient.medico}</span></div>
                      <div className="info-row"><span className="label">Diagnóstico</span><span className="value">{patient.diagnostico}</span></div>
                      <div className="info-row"><span className="label">Sesiones médicas</span><span className="value">{patient.nSesionesMedicas}</span></div>
                    </div>
                  </div>
                </div>
                <div className="card">
                  <div className="card-header"><h3>Área psicológica</h3></div>
                  <div className="card-body">
                    <div className="info-grid" style={{gridTemplateColumns:'1fr'}}>
                      <div className="info-row"><span className="label">Evaluación psi.</span><span><StatusBadge state={patient.evaluacionPsicologica}/></span></div>
                      <div className="info-row"><span className="label">Psicólogo</span><span className="value">{patient.psicologo}</span></div>
                      <div className="info-row"><span className="label">Sesiones psi.</span><span className="value">{patient.nSesionesPsicologicas}</span></div>
                      <div className="info-row"><span className="label">Encuesta satisf.</span><span><StatusBadge state={patient.encuestaSatisfaccion}/></span></div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="card">
                <div className="card-header"><h3>Resumen de dimensiones</h3></div>
                <div className="card-body">
                  <div style={{display:'grid', gridTemplateColumns:'repeat(4, 1fr)', gap:12}}>
                    <div style={{padding:14, background:'var(--warn-50)', borderRadius:8, border:'1px solid var(--warn-100)'}}>
                      <div style={{fontSize:11, color:'var(--warn-700)', fontWeight:600, textTransform:'uppercase', letterSpacing:'0.04em'}}>Licencias</div>
                      <div style={{fontSize:22, fontWeight:700, color:'var(--warn-700)', marginTop:4}}>{lic.length}</div>
                      <div style={{fontSize:11, color:'var(--warn-700)', marginTop:2}}>{totalDiasLic} días acumulados</div>
                    </div>
                    <div style={{padding:14, background:'#f4f0ff', borderRadius:8, border:'1px solid #e9d7fe'}}>
                      <div style={{fontSize:11, color:'#5925dc', fontWeight:600, textTransform:'uppercase', letterSpacing:'0.04em'}}>Recetas</div>
                      <div style={{fontSize:22, fontWeight:700, color:'#5925dc', marginTop:4}}>{rec.length}</div>
                      <div style={{fontSize:11, color:'#5925dc', marginTop:2}}>{rec.filter(r=>r.estado==='Activa').length} activas</div>
                    </div>
                    <div style={{padding:14, background:'var(--success-50)', borderRadius:8, border:'1px solid var(--success-100)'}}>
                      <div style={{fontSize:11, color:'var(--success-700)', fontWeight:600, textTransform:'uppercase', letterSpacing:'0.04em'}}>Controles</div>
                      <div style={{fontSize:22, fontWeight:700, color:'var(--success-700)', marginTop:4}}>{patient.nSesionesMedicas + patient.nSesionesPsicologicas}</div>
                      <div style={{fontSize:11, color:'var(--success-700)', marginTop:2}}>Próximo: {fmtDate(patient.proxControl)}</div>
                    </div>
                    <div style={{padding:14, background:'var(--brand-50)', borderRadius:8, border:'1px solid var(--brand-100)'}}>
                      <div style={{fontSize:11, color:'var(--brand-700)', fontWeight:600, textTransform:'uppercase', letterSpacing:'0.04em'}}>Plazo ISL</div>
                      <div style={{fontSize:22, fontWeight:700, color:'var(--brand-700)', marginTop:4}}>{patient.plazoInformeDias}d</div>
                      <div style={{fontSize:11, color:'var(--brand-700)', marginTop:2}}>{patient.envioInforme}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {tab === 'licencias' && (
            <div className="card flush">
              <div className="card-header"><h3>Licencias médicas · {lic.length}</h3>
                <div className="actions"><button className="btn primary sm"><Icon name="plus" size={12}/>Nueva licencia</button></div>
              </div>
              {lic.length === 0 ? <div className="empty"><Icon name="file" size={32} color="var(--ink-300)"/><h4>Sin licencias</h4><p>Este paciente no registra licencias médicas.</p></div> : (
                <table className="data-table">
                  <thead><tr><th>Folio LM</th><th>Tipo</th><th>Reposo</th><th>Inicio</th><th>Término</th><th>Días</th><th>ISL</th><th>EEAG</th></tr></thead>
                  <tbody>{lic.map(l => (
                    <tr key={l.id}>
                      <td className="mono">{l.folioLM}</td>
                      <td>Tipo {l.tipoLicencia}</td>
                      <td>{l.tipoReposo}</td>
                      <td>{fmtDate(l.fechaInicio)}</td>
                      <td>{fmtDate(l.fechaTermino)}</td>
                      <td className="mono"><b>{l.dias}</b></td>
                      <td><StatusBadge state={l.envioISL}/></td>
                      <td className="mono">{l.eeag}</td>
                    </tr>
                  ))}</tbody>
                </table>
              )}
              {lic.length > 0 && <div style={{padding:'12px 18px', background:'var(--warn-50)', borderTop:'1px solid var(--warn-100)', fontSize:12.5, color:'var(--warn-700)', fontWeight:600, display:'flex', alignItems:'center', gap:8}}>
                <Icon name="alert" size={14}/>Total acumulado: <b>{totalDiasLic} días</b> en {lic.length} licencias</div>}
            </div>
          )}

          {tab === 'farmacos' && (
            <div className="card flush">
              <div className="card-header"><h3>Recetas · {rec.length}</h3>
                <div className="actions"><button className="btn primary sm"><Icon name="plus" size={12}/>Nueva receta</button></div>
              </div>
              {rec.length === 0 ? <div className="empty"><Icon name="pill" size={32} color="var(--ink-300)"/><h4>Sin recetas</h4></div> : (
                <table className="data-table">
                  <thead><tr><th>Medicamento</th><th>Dosis</th><th>Marca</th><th>Emisión</th><th>Revisión</th><th>Estado</th></tr></thead>
                  <tbody>{rec.map(r => (
                    <tr key={r.id}>
                      <td><b>{r.medicamento}</b></td>
                      <td>{r.dosis} · {r.frecuencia}</td>
                      <td>{r.marca}</td>
                      <td>{fmtDate(r.fechaEmision)}</td>
                      <td>{fmtDate(r.fechaRevision)}</td>
                      <td><StatusBadge state={r.estado}/></td>
                    </tr>
                  ))}</tbody>
                </table>
              )}
            </div>
          )}

          {tab === 'controles' && (
            <div className="card">
              <div className="card-header"><h3>Próximos controles y evaluaciones</h3></div>
              <div className="card-body">
                <div style={{display:'flex', flexDirection:'column', gap:10}}>
                  {[
                    {f: patient.proxControl, tipo:'Control médico', prof: patient.medico, estado: 'Agendado'},
                    {f: addDays(patient.proxControl, 14), tipo:'Control psiquiátrico', prof: patient.medico, estado: 'Pendiente agenda'},
                    {f: addDays(patient.proxControl, 7), tipo:'Sesión psicológica', prof: patient.psicologo, estado: 'Agendado'},
                  ].map((c,i) => (
                    <div key={i} style={{display:'flex', alignItems:'center', gap:14, padding:12, background:'var(--ink-50)', borderRadius:8, border:'1px solid var(--ink-100)'}}>
                      <div style={{width:52, textAlign:'center', padding:'6px 0', background:'#fff', borderRadius:6, border:'1px solid var(--ink-200)'}}>
                        <div style={{fontSize:10, color:'var(--ink-500)', textTransform:'uppercase', fontWeight:600}}>{['Ene','Feb','Mar','Abr','May','Jun'][c.f.getMonth()] || 'Abr'}</div>
                        <div style={{fontSize:17, fontWeight:700, color:'var(--ink-900)'}}>{c.f.getDate()}</div>
                      </div>
                      <div style={{flex:1}}>
                        <div style={{fontWeight:600, fontSize:13}}>{c.tipo}</div>
                        <div style={{fontSize:12, color:'var(--ink-500)'}}>{c.prof}</div>
                      </div>
                      <StatusBadge state={c.estado === 'Agendado' ? 'Realizada' : 'Pendiente'}/>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {tab === 'observaciones' && (
            <div className="card">
              <div className="card-header"><h3>Log de auditoría y observaciones</h3></div>
              <div className="card-body">
                <div style={{display:'flex', flexDirection:'column', gap:14}}>
                  {[
                    {u:'María García', a:'Registró nuevo ingreso', t:fmtDate(patient.fechaIngreso)},
                    {u:patient.medico, a:'Evaluación médica · Diagnóstico: ' + patient.diagnostico, t:fmtDate(patient.fechaAcogida)},
                    {u:patient.psicologo, a:'Primera sesión psicológica', t:fmtDate(addDays(patient.fechaAcogida, 7))},
                    {u:'Sistema', a:'Alerta automática: licencia próxima a vencer', t:'Hoy 09:15'},
                  ].map((e,i) => (
                    <div key={i} style={{display:'flex', gap:12, paddingBottom:14, borderBottom: i<3?'1px solid var(--ink-100)':'none'}}>
                      <div className="avatar" style={{background:'var(--ink-300)', width:28, height:28, fontSize:10}}>{e.u.split(' ').map(x=>x[0]).slice(0,2).join('')}</div>
                      <div style={{flex:1}}>
                        <div style={{fontSize:12.5}}><b>{e.u}</b> {e.a}</div>
                        <div style={{fontSize:11, color:'var(--ink-500)', marginTop:2}}>{e.t}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

const PageIngresos = ({ onOpenPatient }) => {
  const [q, setQ] = React.useState('');
  const [estado, setEstado] = React.useState('todos');
  const filtered = PATIENTS.filter(p => {
    if (estado !== 'todos' && p.estado !== estado) return false;
    if (!q) return true;
    const s = q.toLowerCase();
    return p.nombre.toLowerCase().includes(s) || p.rut.includes(q) || p.folio.includes(q);
  });

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Ingresos y gestión de pacientes</h1>
          <p>{PATIENTS.length} registros · {PATIENTS.filter(p=>p.estado==='Activo').length} activos · Actualizado hoy</p>
        </div>
        <div className="actions">
          <button className="btn ghost"><Icon name="download" size={14}/>Exportar Excel</button>
          <button className="btn ghost"><Icon name="filter" size={14}/>Filtros avanzados</button>
          <button className="btn primary"><Icon name="plus" size={14}/>Nuevo ingreso</button>
        </div>
      </div>

      <div className="card flush">
        <div className="filters-bar">
          <div className="search">
            <Icon name="search" size={14} color="var(--ink-400)"/>
            <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Buscar por RUT, folio o nombre…"/>
          </div>
          <select value={estado} onChange={e=>setEstado(e.target.value)}>
            <option value="todos">Estado: Todos</option>
            {['Activo','En tratamiento','Pendiente','Cerrado','Derivado'].map(e => <option key={e}>{e}</option>)}
          </select>
          <select><option>Región: Todas</option>{window.REGIONES.map(r=><option key={r}>{r}</option>)}</select>
          <select><option>Derivación: Todas</option>{window.TIPOS_DERIVACION.map(t=><option key={t}>{t}</option>)}</select>
          <div style={{marginLeft:'auto', fontSize:12, color:'var(--ink-500)'}}>{filtered.length} resultados</div>
        </div>
        <div style={{overflow:'auto'}}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Folio</th><th>Paciente</th><th>RUT</th><th>Región</th>
                <th>Derivación</th><th>Empresa</th><th>Ingreso</th>
                <th>Eval. Méd.</th><th>Eval. Psi.</th><th>Estado</th><th style={{textAlign:'right'}}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(p => (
                <tr key={p.folio} onClick={()=>onOpenPatient(p)}>
                  <td className="mono">{p.folio}</td>
                  <td>
                    <div style={{fontWeight:600}}>{p.nombre}</div>
                    <div style={{fontSize:11, color:'var(--ink-500)'}}>{p.diagnostico.split('(')[0].trim()}</div>
                  </td>
                  <td className="mono">{p.rut}</td>
                  <td>{p.region}</td>
                  <td style={{fontSize:12}}>{p.tipoDerivacion}</td>
                  <td style={{fontSize:12, maxWidth:200, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{p.empresa}</td>
                  <td className="mono" style={{fontSize:12}}>{fmtDate(p.fechaIngreso)}</td>
                  <td><StatusBadge state={p.evaluacionMedica}/></td>
                  <td><StatusBadge state={p.evaluacionPsicologica}/></td>
                  <td><StatusBadge state={p.estado}/></td>
                  <td onClick={e=>e.stopPropagation()}>
                    <div className="row-actions" style={{justifyContent:'flex-end'}}>
                      <button title="Ver"><Icon name="eye" size={14}/></button>
                      <button title="Editar"><Icon name="edit" size={14}/></button>
                      <button title="Exportar"><Icon name="share" size={14}/></button>
                      <button title="Eliminar" className="danger"><Icon name="trash" size={14}/></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{padding:'12px 18px', borderTop:'1px solid var(--ink-100)', display:'flex', justifyContent:'space-between', alignItems:'center', fontSize:12, color:'var(--ink-500)'}}>
          <span>Mostrando 1–{filtered.length} de {PATIENTS.length}</span>
          <div style={{display:'flex', gap:6, alignItems:'center'}}>
            <button className="btn ghost sm"><Icon name="chevron-left" size={12}/></button>
            <button className="btn primary sm">1</button>
            <button className="btn ghost sm">2</button>
            <button className="btn ghost sm">3</button>
            <button className="btn ghost sm"><Icon name="chevron-right" size={12}/></button>
          </div>
        </div>
      </div>
    </div>
  );
};

window.PageIngresos = PageIngresos;
window.PatientSheet = PatientSheet;
