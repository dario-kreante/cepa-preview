/* Shell: Sidebar + Topbar + Alerts panel
   Depends on: Icon (global), ALERTS (global) */

const NAV_ITEMS = [
  { key: 'dashboard',   label: 'Dashboard',           icon: 'dashboard' },
  { key: 'ingresos',    label: 'Ingresos y pacientes', icon: 'users' },
  { key: 'licencias',   label: 'Licencias médicas',    icon: 'file', badge: 4 },
  { key: 'farmacos',    label: 'Gestión de fármacos',  icon: 'pill' },
  { key: 'controles',   label: 'Controles médicos',    icon: 'stethoscope' },
  { key: 'ept',         label: 'Seguimiento EPT',      icon: 'briefcase', badge: 2 },
  { key: 'reintegro',   label: 'Seguimiento reintegro',icon: 'repeat' },
  { key: 'auditoria',   label: 'Auditoría',            icon: 'shield' },
  { key: 'agenda',      label: 'Agendamiento',         icon: 'calendar' },
  { key: 'reportes',    label: 'Reportería',           icon: 'chart' },
];

const Sidebar = ({ current, onNav, collapsed, onToggle }) => (
  <aside className="sidebar-root">
    <div className="brand-block">
      <div className="brand-mark">CP</div>
      <div className="brand-text">
        <strong>CEPA</strong>
        <span>Universidad de Talca</span>
      </div>
    </div>

    <div className="nav-section">
      <div className="nav-section-title">General</div>
      {NAV_ITEMS.slice(0,1).map(it => (
        <div key={it.key} className={'nav-item' + (current===it.key?' active':'')} onClick={() => onNav(it.key)}>
          <Icon name={it.icon} size={17}/>
          <span>{it.label}</span>
        </div>
      ))}
    </div>

    <div className="nav-section">
      <div className="nav-section-title">Módulos clínicos</div>
      {NAV_ITEMS.slice(1,8).map(it => (
        <div key={it.key} className={'nav-item' + (current===it.key?' active':'')} onClick={() => onNav(it.key)}>
          <Icon name={it.icon} size={17}/>
          <span>{it.label}</span>
          {it.badge && <span className="badge">{it.badge}</span>}
        </div>
      ))}
    </div>

    <div className="nav-section">
      <div className="nav-section-title">Operación</div>
      {NAV_ITEMS.slice(8).map(it => (
        <div key={it.key} className={'nav-item' + (current===it.key?' active':'')} onClick={() => onNav(it.key)}>
          <Icon name={it.icon} size={17}/>
          <span>{it.label}</span>
        </div>
      ))}
    </div>

    <div className="nav-section" style={{borderTop: '1px solid var(--brand-800)', marginTop: 12}}>
      <div className="nav-item" onClick={onToggle}>
        <Icon name={collapsed ? 'chevron-right' : 'chevron-left'} size={17}/>
        <span>Colapsar</span>
      </div>
    </div>
  </aside>
);

const Topbar = ({ title, crumbs, onSearchClick, role, setRole, onToggleAlerts, alertsHidden }) => (
  <header className="topbar-root">
    <div>
      <div className="topbar-title">{title}</div>
      {crumbs && <div className="topbar-crumbs">{crumbs}</div>}
    </div>

    <div className="topbar-spacer"/>

    <div className="topbar-search" onClick={onSearchClick}>
      <Icon name="search" size={15} color="var(--ink-400)"/>
      <input placeholder="Buscar paciente por RUT, folio o nombre…"/>
      <span className="mono" style={{fontSize:11, color:'var(--ink-400)', background:'var(--ink-200)', padding:'2px 5px', borderRadius:4}}>⌘K</span>
    </div>

    <div className="topbar-kpi">
      <span className="dot"/>
      <span>{window.DASHBOARD_KPIS.pacientesActivos}</span>
      <span>casos activos</span>
    </div>
    <div className="topbar-kpi danger">
      <span className="dot"/>
      <b>{window.DASHBOARD_KPIS.alertasCriticas}</b>
      <span>críticas</span>
    </div>

    <button className="icon-btn" onClick={onToggleAlerts} title={alertsHidden ? 'Mostrar alertas' : 'Ocultar alertas'}>
      <Icon name="bell" size={18}/>
      {!alertsHidden && <span className="pulse"/>}
    </button>

    <div className="user-chip">
      <div className="avatar">MG</div>
      <div>
        <div className="name">María García</div>
        <div className="role">{role}</div>
      </div>
      <Icon name="chevron-down" size={14} color="var(--ink-400)"/>
    </div>
  </header>
);

const AlertsPanel = ({ onItemClick }) => {
  const [tab, setTab] = React.useState('todas');
  const filtered = tab === 'todas' ? window.ALERTS : window.ALERTS.filter(a => a.tipo === tab);
  const criticas = window.ALERTS.filter(a => a.tipo === 'danger').length;

  return (
    <aside className="alerts-root">
      <div className="alerts-panel-header">
        <Icon name="bell" size={16} color="var(--brand-700)"/>
        <h3>Alertas y tareas</h3>
        <span className="count">{criticas}</span>
      </div>
      <div className="alerts-tabs">
        {['todas','danger','warn','info'].map(t => (
          <button key={t}
            className={'alerts-tab' + (tab===t?' active':'')}
            onClick={() => setTab(t)}>
            {t==='todas'?'Todas': t==='danger'?'Críticas': t==='warn'?'Próximas':'Informativas'}
          </button>
        ))}
      </div>
      <div style={{padding: '8px 14px', background: 'var(--ink-50)', borderBottom:'1px solid var(--ink-100)'}}>
        <div style={{fontSize:11, color:'var(--ink-500)', fontWeight:600, textTransform:'uppercase', letterSpacing:'0.04em'}}>Hoy · Viernes 18 abr 2026</div>
      </div>
      {filtered.map(a => (
        <div key={a.id} className="alert-item" onClick={() => onItemClick && onItemClick(a)}>
          <div className={'alert-dot ' + a.tipo}>
            <Icon name={a.tipo==='danger'?'alert': a.tipo==='warn'?'clock': a.tipo==='success'?'check':'bell'} size={14}/>
          </div>
          <div className="alert-body">
            <div className="title">{a.titulo}</div>
            <div className="desc">{a.paciente} · Folio {a.folio}</div>
            <div className="meta">
              <span>{a.modulo}</span>
              <span>•</span>
              <span>{a.hora}</span>
            </div>
          </div>
        </div>
      ))}
      <div style={{padding:'14px 18px', borderTop:'1px solid var(--ink-100)', background:'var(--ink-50)'}}>
        <div style={{fontSize:11, color:'var(--ink-500)', fontWeight:600, textTransform:'uppercase', letterSpacing:'0.04em', marginBottom:8}}>Accesos rápidos</div>
        <div style={{display:'flex', flexDirection:'column', gap:6}}>
          <button className="btn ghost sm" style={{justifyContent:'flex-start'}}><Icon name="plus" size={13}/>Nuevo ingreso</button>
          <button className="btn ghost sm" style={{justifyContent:'flex-start'}}><Icon name="file" size={13}/>Registrar licencia</button>
          <button className="btn ghost sm" style={{justifyContent:'flex-start'}}><Icon name="pill" size={13}/>Nueva receta</button>
        </div>
      </div>
    </aside>
  );
};

window.Sidebar = Sidebar;
window.Topbar = Topbar;
window.AlertsPanel = AlertsPanel;
