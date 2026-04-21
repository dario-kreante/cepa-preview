/* Módulos de seguimiento: EPT, Reintegro, Auditoría */

const PageEPT = () => {
  const epts = window.EPTS;
  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Seguimiento EPT</h1>
          <p>Evaluaciones de puesto de trabajo · Gestión con empleadores e ISL</p>
        </div>
        <div className="actions">
          <button className="btn ghost"><Icon name="mail" size={14}/>Correos plantilla</button>
          <button className="btn ghost"><Icon name="download" size={14}/>Reporte mensual</button>
          <button className="btn primary"><Icon name="plus" size={14}/>Nueva EPT</button>
        </div>
      </div>

      <div className="kpi-grid" style={{gridTemplateColumns:'repeat(4, 1fr)', marginBottom:20}}>
        <div className="kpi-tile"><div className="label">EPT en proceso</div><div className="value">{epts.length}</div></div>
        <div className="kpi-tile"><div className="label">Pendientes ISL</div><div className="value" style={{color:'var(--warn-700)'}}>{epts.filter(e=>e.estadoEnvio!=='Enviado').length}</div></div>
        <div className="kpi-tile"><div className="label">Con testigos</div><div className="value">{epts.filter(e=>e.testigos).length}</div></div>
        <div className="kpi-tile"><div className="label">Plazos excedidos</div><div className="value" style={{color:'var(--danger-600)'}}>2</div></div>
      </div>

      <div className="card flush">
        <div className="filters-bar">
          <div className="search"><Icon name="search" size={14} color="var(--ink-400)"/><input placeholder="EPT, paciente o empresa…"/></div>
          <select><option>Tipo: Todos</option><option>EM</option><option>EPS</option><option>EM+EPS</option></select>
          <select><option>EPTista: Todos</option><option>Ps. Lorena Baeza</option><option>Ps. Tomás Jiménez</option><option>Ps. Sofía Retamal</option></select>
          <select><option>Estado ISL: Todos</option><option>Enviado</option><option>Pendiente</option></select>
          <div style={{marginLeft:'auto', fontSize:12, color:'var(--ink-500)'}}>{epts.length} EPTs</div>
        </div>
        <div style={{overflow:'auto'}}>
        <table className="data-table">
          <thead><tr>
            <th>Nº EPT</th><th>Paciente</th><th>Empresa</th><th>Tipo</th>
            <th>EPTista</th><th>Factor riesgo</th><th>Entrevistas</th><th>Plazo inf.</th>
            <th>Plazo ISL</th><th>Envío ISL</th><th>Estado caso</th>
          </tr></thead>
          <tbody>{epts.map(e => (
            <tr key={e.folio}>
              <td className="mono"><b>{e.numero}</b><div style={{fontSize:11, color:'var(--ink-500)', fontWeight:400}}>Folio {e.folio}</div></td>
              <td><b>{e.paciente}</b><div style={{fontSize:11, color:'var(--ink-500)'}}>{e.rut}</div></td>
              <td style={{fontSize:12, maxWidth:180}}>
                <div>{e.razonSocial}</div>
                <div style={{fontSize:11, color:'var(--ink-500)'}}>{e.unidad} · {e.cargo}</div>
              </td>
              <td><span className="badge-pill info">{e.tipoEvaluacion}</span></td>
              <td style={{fontSize:12}}>{e.eptista}</td>
              <td style={{fontSize:12}}>{e.factorRiesgo}</td>
              <td className="mono">{e.nEntrevistas}{e.testigos && ` +${e.cantidadTestigos}t`}</td>
              <td className="mono">{e.plazoInformeEPT}d</td>
              <td className="mono">{e.plazoPortalISL}d</td>
              <td><StatusBadge state={e.estadoEnvio==='Enviado'?'Enviado':e.estadoEnvio}/></td>
              <td><StatusBadge state={e.estadoCaso}/></td>
            </tr>
          ))}</tbody>
        </table>
        </div>
      </div>
    </div>
  );
};

const PageReintegro = () => {
  const rs = window.REINTEGROS;
  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Seguimiento de reintegro</h1>
          <p>RECA, medidas correctivas, verificación y cierre de caso</p>
        </div>
        <div className="actions">
          <button className="btn ghost"><Icon name="download" size={14}/>Exportar</button>
          <button className="btn primary"><Icon name="plus" size={14}/>Solicitar RECA</button>
        </div>
      </div>

      <div className="kpi-grid" style={{gridTemplateColumns:'repeat(4, 1fr)', marginBottom:20}}>
        <div className="kpi-tile"><div className="label">En proceso</div><div className="value">{rs.filter(r=>r.estadoReintegro==='En proceso').length}</div></div>
        <div className="kpi-tile"><div className="label">Reintegrados</div><div className="value" style={{color:'var(--success-700)'}}>{rs.filter(r=>r.estadoReintegro==='Reintegrado').length}</div></div>
        <div className="kpi-tile"><div className="label">RECA pendientes</div><div className="value">{rs.filter(r=>r.solicitudRECA==='Pendiente').length}</div></div>
        <div className="kpi-tile"><div className="label">Medidas verificadas</div><div className="value">{rs.filter(r=>r.verificacion==='Verificada').length}</div></div>
      </div>

      <div className="card flush">
        <div className="filters-bar">
          <div className="search"><Icon name="search" size={14} color="var(--ink-400)"/><input placeholder="Paciente, empresa, RECA…"/></div>
          <select><option>Estado: Todos</option><option>En proceso</option><option>Reintegrado</option><option>Pendiente</option></select>
          <select><option>Tipo RECA: Todos</option><option>EP</option><option>EC</option></select>
          <select><option>Derivación: Todas</option>{window.TIPOS_DERIVACION.map(t=><option key={t}>{t}</option>)}</select>
          <div style={{marginLeft:'auto', fontSize:12, color:'var(--ink-500)'}}>{rs.length} casos</div>
        </div>
        <div style={{overflow:'auto'}}>
        <table className="data-table">
          <thead><tr>
            <th>Paciente</th><th>Derivación</th><th>RECA</th><th>Fecha RECA</th>
            <th>Tipo</th><th>Riesgos calificados</th><th>Medidas</th><th>Verificación</th>
            <th>Estado reintegro</th><th>Fecha reintegro</th><th>Alta</th>
          </tr></thead>
          <tbody>{rs.map(r => (
            <tr key={r.folio}>
              <td><b>{r.paciente}</b><div style={{fontSize:11, color:'var(--ink-500)'}}>Folio {r.folio}</div></td>
              <td style={{fontSize:12}}>{r.tipoDerivacion}</td>
              <td className="mono">{r.numeroRECA}</td>
              <td className="mono" style={{fontSize:12}}>{fmtDate(r.fechaRECA)}</td>
              <td><span className="badge-pill purple">{r.tipoRECA}</span></td>
              <td style={{fontSize:12}}>{r.riesgosCalificados}</td>
              <td><StatusBadge state={r.medidasCorrectivas==='Implementadas'?'Realizada':r.medidasCorrectivas}/></td>
              <td><StatusBadge state={r.verificacion==='Verificada'?'Realizada':r.verificacion}/></td>
              <td><StatusBadge state={r.estadoReintegro}/></td>
              <td className="mono" style={{fontSize:12}}>{fmtDate(r.fechaReintegro)}</td>
              <td style={{fontSize:12}}>{r.tipoAlta}</td>
            </tr>
          ))}</tbody>
        </table>
        </div>
      </div>
    </div>
  );
};

const PageAuditoria = () => {
  // Consolidado: una fila por paciente con estado de cada hito del proceso
  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Auditoría · Vista consolidada</h1>
          <p>Trazabilidad del proceso completo por paciente (DIEP → Alta)</p>
        </div>
        <div className="actions">
          <button className="btn ghost"><Icon name="filter" size={14}/>Filtros</button>
          <button className="btn ghost"><Icon name="download" size={14}/>Exportar Excel</button>
          <button className="btn primary"><Icon name="share" size={14}/>Compartir con ISL</button>
        </div>
      </div>

      <div className="card flush">
        <div className="filters-bar">
          <div className="search"><Icon name="search" size={14} color="var(--ink-400)"/><input placeholder="Paciente, RUT, folio…"/></div>
          <select><option>Mes: Todos</option><option>Enero</option><option>Febrero</option><option>Marzo</option><option>Abril</option></select>
          <select><option>Estado: Todos</option>{window.ESTADOS.map(e=><option key={e}>{e}</option>)}</select>
          <select><option>Región: Todas</option>{window.REGIONES.map(r=><option key={r}>{r}</option>)}</select>
          <div style={{marginLeft:'auto', fontSize:12, color:'var(--ink-500)'}}>{PATIENTS.length} pacientes</div>
        </div>
        <div style={{overflow:'auto', maxHeight: 'calc(100vh - 340px)'}}>
        <table className="data-table">
          <thead>
            <tr>
              <th rowSpan="2">Folio</th>
              <th rowSpan="2">Paciente</th>
              <th rowSpan="2">RUT</th>
              <th rowSpan="2">Mes</th>
              <th colSpan="3" style={{textAlign:'center', borderLeft:'1px solid var(--ink-200)', borderRight:'1px solid var(--ink-200)'}}>Ingreso</th>
              <th colSpan="2" style={{textAlign:'center', borderRight:'1px solid var(--ink-200)'}}>Evaluaciones</th>
              <th colSpan="3" style={{textAlign:'center', borderRight:'1px solid var(--ink-200)'}}>Informe ISL</th>
              <th colSpan="2" style={{textAlign:'center', borderRight:'1px solid var(--ink-200)'}}>RECA</th>
              <th colSpan="3" style={{textAlign:'center'}}>Cierre</th>
            </tr>
            <tr>
              <th style={{borderLeft:'1px solid var(--ink-200)'}}>F. ingreso</th><th>DIEP</th><th style={{borderRight:'1px solid var(--ink-200)'}}>Acogida</th>
              <th>Médica</th><th style={{borderRight:'1px solid var(--ink-200)'}}>Psi.</th>
              <th>Plazo</th><th>Obstac.</th><th style={{borderRight:'1px solid var(--ink-200)'}}>Envío</th>
              <th>Tipo</th><th style={{borderRight:'1px solid var(--ink-200)'}}>N°</th>
              <th>Estado</th><th>Alta</th><th>Encuesta</th>
            </tr>
          </thead>
          <tbody>{PATIENTS.map(p => (
            <tr key={p.folio}>
              <td className="mono"><b>{p.folio}</b></td>
              <td><b>{p.nombre}</b></td>
              <td className="mono" style={{fontSize:11}}>{p.rut}</td>
              <td>{p.mes}</td>
              <td className="mono" style={{fontSize:11, borderLeft:'1px solid var(--ink-100)'}}>{fmtDate(p.fechaIngreso)}</td>
              <td className="mono" style={{fontSize:11}}>{fmtDate(p.fechaDIEP)}</td>
              <td className="mono" style={{fontSize:11, borderRight:'1px solid var(--ink-100)'}}>{fmtDate(p.fechaAcogida)}</td>
              <td><StatusBadge state={p.evaluacionMedica}/></td>
              <td style={{borderRight:'1px solid var(--ink-100)'}}><StatusBadge state={p.evaluacionPsicologica}/></td>
              <td className="mono">{p.plazoInformeDias}d</td>
              <td>{p.obstaculizacion ? <span className="badge-pill danger">Sí</span> : <span className="badge-pill neutral">No</span>}</td>
              <td style={{borderRight:'1px solid var(--ink-100)'}}><StatusBadge state={p.envioInforme}/></td>
              <td><span className={'badge-pill ' + (p.recaTipo==='EP'?'info':'purple')}>{p.recaTipo}</span></td>
              <td className="mono" style={{fontSize:11, borderRight:'1px solid var(--ink-100)'}}>{p.recaNumero}</td>
              <td><StatusBadge state={p.estado}/></td>
              <td style={{fontSize:11}}>{p.tipoAlta}</td>
              <td><StatusBadge state={p.encuestaSatisfaccion}/></td>
            </tr>
          ))}</tbody>
        </table>
        </div>
      </div>
    </div>
  );
};

window.PageEPT = PageEPT;
window.PageReintegro = PageReintegro;
window.PageAuditoria = PageAuditoria;
