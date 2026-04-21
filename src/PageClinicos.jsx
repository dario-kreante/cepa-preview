/* Módulos clínicos: Licencias, Fármacos, Controles */

const PageLicencias = () => {
  const [q, setQ] = React.useState('');
  const lics = window.LICENCIAS;
  const filtered = lics.filter(l => !q || l.paciente.toLowerCase().includes(q.toLowerCase()) || l.folioLM.includes(q.toUpperCase()) || l.rut.includes(q));
  const today = new Date(2026, 3, 18);
  const activas = lics.filter(l => l.fechaTermino >= today);
  const totalDias = lics.reduce((s,l)=>s+l.dias,0);
  const promDias = Math.round(totalDias / Math.max(1,lics.length));

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Licencias médicas</h1>
          <p>Registro, seguimiento y envío a ISL · Cálculo automático de días y plazos</p>
        </div>
        <div className="actions">
          <button className="btn ghost"><Icon name="upload" size={14}/>Importar CSV</button>
          <button className="btn ghost"><Icon name="send" size={14}/>Envío masivo ISL</button>
          <button className="btn primary"><Icon name="plus" size={14}/>Nueva licencia</button>
        </div>
      </div>

      <div className="kpi-grid" style={{gridTemplateColumns:'repeat(4, 1fr)', marginBottom:20}}>
        <div className="kpi-tile"><div className="label">Licencias totales</div><div className="value">{lics.length}</div><div style={{fontSize:11, color:'var(--ink-500)'}}>últimos 6 meses</div></div>
        <div className="kpi-tile"><div className="label">Activas hoy</div><div className="value" style={{color:'var(--warn-700)'}}>{activas.length}</div><div style={{fontSize:11, color:'var(--ink-500)'}}>vencen próximamente 7</div></div>
        <div className="kpi-tile"><div className="label">Días acumulados</div><div className="value">{totalDias}</div><div style={{fontSize:11, color:'var(--ink-500)'}}>promedio: {promDias} días/LM</div></div>
        <div className="kpi-tile"><div className="label">Pendientes ISL</div><div className="value" style={{color:'var(--danger-600)'}}>{lics.filter(l=>l.envioISL==='Pendiente').length}</div><div style={{fontSize:11, color:'var(--danger-600)'}}>requieren envío</div></div>
      </div>

      <div className="card flush">
        <div className="filters-bar">
          <div className="search">
            <Icon name="search" size={14} color="var(--ink-400)"/>
            <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Folio LM, RUT o paciente…"/>
          </div>
          <select><option>Tipo: Todos</option><option>Tipo 1</option><option>Tipo 5</option><option>Tipo 6</option></select>
          <select><option>Reposo: Todos</option><option>Total</option><option>Parcial</option></select>
          <select><option>ISL: Todos</option><option>Enviado</option><option>Pendiente</option></select>
          <select><option>Región: Todas</option>{window.REGIONES.map(r=><option key={r}>{r}</option>)}</select>
          <div style={{marginLeft:'auto', fontSize:12, color:'var(--ink-500)'}}>{filtered.length} licencias</div>
        </div>
        <table className="data-table">
          <thead><tr>
            <th>Folio LM</th><th>Paciente</th><th>RUT</th><th>Tipo</th><th>Reposo</th>
            <th>Inicio</th><th>Término</th><th>Días</th><th>Vence en</th><th>EEAG</th><th>ISL</th><th></th>
          </tr></thead>
          <tbody>
            {filtered.slice(0,20).map(l => {
              const dd = diffDays(today, l.fechaTermino);
              const urg = dd < 0 ? 'neutral' : dd < 3 ? 'danger' : dd < 7 ? 'warn' : 'success';
              return (
                <tr key={l.id}>
                  <td className="mono">{l.folioLM}</td>
                  <td><b>{l.paciente}</b><div style={{fontSize:11, color:'var(--ink-500)'}}>Folio {l.folio}</div></td>
                  <td className="mono">{l.rut}</td>
                  <td>Tipo {l.tipoLicencia}</td>
                  <td>{l.tipoReposo}</td>
                  <td className="mono">{fmtDate(l.fechaInicio)}</td>
                  <td className="mono">{fmtDate(l.fechaTermino)}</td>
                  <td className="mono"><b>{l.dias}</b></td>
                  <td><span className={'badge-pill ' + urg}>{dd < 0 ? 'Vencida' : dd + ' días'}</span></td>
                  <td className="mono">{l.eeag}</td>
                  <td><StatusBadge state={l.envioISL}/></td>
                  <td><div className="row-actions"><button><Icon name="eye" size={13}/></button><button><Icon name="send" size={13}/></button><button><Icon name="more" size={13}/></button></div></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const PageFarmacos = () => {
  const recetas = window.RECETAS;
  const [q, setQ] = React.useState('');
  const filtered = recetas.filter(r => !q || r.paciente.toLowerCase().includes(q.toLowerCase()) || r.medicamento.toLowerCase().includes(q.toLowerCase()));
  const activas = recetas.filter(r=>r.estado==='Activa').length;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Gestión de fármacos</h1>
          <p>Recetas, retiros en farmacia y gestión con Socorro Ahumada</p>
        </div>
        <div className="actions">
          <button className="btn ghost"><Icon name="download" size={14}/>Reporte de retiros</button>
          <button className="btn ghost"><Icon name="send" size={14}/>Enviar a Ahumada</button>
          <button className="btn primary"><Icon name="plus" size={14}/>Nueva receta</button>
        </div>
      </div>

      <div className="kpi-grid" style={{gridTemplateColumns:'repeat(4, 1fr)', marginBottom:20}}>
        <div className="kpi-tile"><div className="label">Recetas activas</div><div className="value">{activas}</div></div>
        <div className="kpi-tile"><div className="label">Pendientes envío Ahumada</div><div className="value" style={{color:'var(--warn-700)'}}>5</div></div>
        <div className="kpi-tile"><div className="label">Gestiones Socorro</div><div className="value">{recetas.filter(r=>r.gestionSocorro1).length}</div></div>
        <div className="kpi-tile"><div className="label">Cambios de esquema (mes)</div><div className="value">{recetas.filter(r=>r.cambioEsquema).length}</div></div>
      </div>

      <div className="card flush">
        <div className="filters-bar">
          <div className="search">
            <Icon name="search" size={14} color="var(--ink-400)"/>
            <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Paciente, medicamento, médico…"/>
          </div>
          <select><option>Estado: Todos</option><option>Activa</option><option>Suspendida</option></select>
          <select><option>Médico: Todos</option>{window.MEDICOS.map(m=><option key={m}>{m}</option>)}</select>
          <select><option>Marca: Todas</option><option>Genérico</option><option>Lab. Chile</option><option>Saval</option></select>
          <div style={{marginLeft:'auto', fontSize:12, color:'var(--ink-500)'}}>{filtered.length} recetas</div>
        </div>
        <table className="data-table">
          <thead><tr><th>Paciente</th><th>Medicamento</th><th>Dosis</th><th>Médico</th><th>Emisión</th><th>Revisión</th><th>Ahumada</th><th>Socorro 1</th><th>Socorro 2</th><th>Cambio</th><th>Estado</th></tr></thead>
          <tbody>{filtered.map(r => (
            <tr key={r.id}>
              <td><b>{r.paciente}</b><div style={{fontSize:11, color:'var(--ink-500)'}}>{r.rut}</div></td>
              <td><b>{r.medicamento}</b><div style={{fontSize:11, color:'var(--ink-500)'}}>{r.marca}</div></td>
              <td>{r.dosis} · {r.frecuencia}</td>
              <td style={{fontSize:12}}>{r.medico}</td>
              <td className="mono" style={{fontSize:12}}>{fmtDate(r.fechaEmision)}</td>
              <td className="mono" style={{fontSize:12}}>{fmtDate(r.fechaRevision)}</td>
              <td className="mono" style={{fontSize:12}}>{fmtDate(r.fechaEnvioAhumada)}</td>
              <td className="mono" style={{fontSize:12}}>{fmtDate(r.gestionSocorro1)}</td>
              <td className="mono" style={{fontSize:12}}>{fmtDate(r.gestionSocorro2)}</td>
              <td>{r.cambioEsquema ? <span className="badge-pill warn">Sí</span> : <span className="badge-pill neutral">No</span>}</td>
              <td><StatusBadge state={r.estado}/></td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
};

const PageControles = () => {
  const controles = window.CONTROLES;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Controles médicos</h1>
          <p>Agenda de controles, GAF, seguimiento post-RECA</p>
        </div>
        <div className="actions">
          <button className="btn ghost"><Icon name="calendar" size={14}/>Vista calendario</button>
          <button className="btn primary"><Icon name="plus" size={14}/>Agendar control</button>
        </div>
      </div>

      <div className="kpi-grid" style={{gridTemplateColumns:'repeat(4, 1fr)', marginBottom:20}}>
        <div className="kpi-tile"><div className="label">Controles esta semana</div><div className="value">{window.DASHBOARD_KPIS.controlesEstaSemana}</div></div>
        <div className="kpi-tile"><div className="label">Atrasados</div><div className="value" style={{color:'var(--danger-600)'}}>3</div></div>
        <div className="kpi-tile"><div className="label">RECAs pendientes</div><div className="value">{controles.filter(c=>c.recaEstado==='Pendiente').length}</div></div>
        <div className="kpi-tile"><div className="label">GAF promedio</div><div className="value">62</div></div>
      </div>

      <div className="card flush">
        <div className="filters-bar">
          <div className="search"><Icon name="search" size={14} color="var(--ink-400)"/><input placeholder="Paciente, RUT o médico…"/></div>
          <select><option>Médico: Todos</option>{window.MEDICOS.map(m=><option key={m}>{m}</option>)}</select>
          <select><option>RECA: Todas</option><option>Recibida</option><option>Pendiente</option><option>En revisión</option></select>
          <select><option>Periodo: Abril 2026</option></select>
          <div style={{marginLeft:'auto', fontSize:12, color:'var(--ink-500)'}}>{controles.length} pacientes</div>
        </div>
        <table className="data-table">
          <thead><tr>
            <th>Paciente</th><th>Médico</th><th>Ingreso</th><th>Próx. control</th>
            <th>Sem. control</th><th>Días LM</th><th>Reposo</th><th>GAF</th><th>RECA</th><th>Fecha RECA</th><th>Post-RECA</th>
          </tr></thead>
          <tbody>{controles.slice(0,20).map(c => (
            <tr key={c.folio}>
              <td><b>{c.paciente}</b><div style={{fontSize:11, color:'var(--ink-500)'}}>{c.rut}</div></td>
              <td style={{fontSize:12}}>{c.medico}</td>
              <td className="mono" style={{fontSize:12}}>{fmtDate(c.fechaIngreso)}</td>
              <td className="mono" style={{fontSize:12}}>{fmtDate(c.proxControl)}</td>
              <td className="mono">Sem {c.semanaControl}</td>
              <td className="mono">{c.diasLicencia}</td>
              <td>{c.tipoReposo}</td>
              <td className="mono">
                <div style={{display:'flex', alignItems:'center', gap:6}}>
                  <div style={{width:40, height:6, background:'var(--ink-100)', borderRadius:3, overflow:'hidden'}}>
                    <div style={{width:c.gaf+'%', height:'100%', background: c.gaf>70?'var(--success-500)':c.gaf>50?'var(--warn-500)':'var(--danger-500)'}}/>
                  </div>
                  {c.gaf}
                </div>
              </td>
              <td><StatusBadge state={c.recaEstado==='Recibida'?'Realizada':c.recaEstado}/></td>
              <td className="mono" style={{fontSize:12}}>{fmtDate(c.fechaRecepcionRECA)}</td>
              <td className="mono" style={{fontSize:12}}>{fmtDate(c.fechaPostRECA)}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
};

window.PageLicencias = PageLicencias;
window.PageFarmacos = PageFarmacos;
window.PageControles = PageControles;
