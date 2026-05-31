from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.main import bp
from functools import wraps
from app.models import Alert, Report
from app.firestore_service import get_firestore_service
from datetime import datetime

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                flash("You don't have permission to access this page.")
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@bp.route('/')
@bp.route('/index')
def index():
    return render_template('index.html', title='Home')

@bp.route('/features')
def features():
    return render_template('features.html', title='Features')

@bp.route('/about')
def about():
    return render_template('about.html', title='About')

@bp.route('/dashboard/admin')
@login_required
@role_required('admin')
def admin_dashboard():
    db = get_firestore_service()
    
    # Get dashboard data from Firestore
    sensor_readings = db.get_sensor_readings(limit=10)
    alerts = db.get_all_alerts(exclude_deleted=True)[:5]
    devices = db.get_all_devices()
    bloom_analysis = db.get_latest_bloom_risk_analysis()
    
    return render_template('admin_dashboard.html', title='Admin Dashboard',
                         sensor_readings=sensor_readings,
                         alerts=alerts,
                         devices=devices,
                         bloom_analysis=bloom_analysis)

@bp.route('/dashboard/authority')
@login_required
@role_required('authority')
def authority_dashboard():
    db = get_firestore_service()
    
    # Get dashboard data from Firestore (no devices for authority)
    sensor_readings = db.get_sensor_readings(limit=10)
    alerts = db.get_all_alerts(exclude_deleted=True)[:5]
    bloom_analysis = db.get_latest_bloom_risk_analysis()
    
    return render_template('authority_dashboard.html', title='Authority Dashboard',
                         sensor_readings=sensor_readings,
                         alerts=alerts,
                         bloom_analysis=bloom_analysis)

@bp.route('/dashboard/authority/alerts')
@login_required
@role_required('authority')
def authority_alerts():
    db = get_firestore_service()
    alerts = db.get_risk_alerts()
    return render_template('authority_alerts.html', title='Authority Alerts', alerts=alerts)

@bp.route('/alerts')
@login_required
def alerts():
    db = get_firestore_service()
    all_alerts = db.get_all_alerts(exclude_deleted=True)
    return render_template('alerts.html', title='Alerts', alerts=all_alerts)

@bp.route('/alerts/mark_all_read', methods=['POST'])
@login_required
def mark_all_read():
    db = get_firestore_service()
    all_alerts = db.get_all_alerts(exclude_deleted=True)
    
    for alert in all_alerts:
        if not alert.get('is_acknowledged', False):
            db.db.collection('alerts').document(alert['id']).update({
                'is_acknowledged': True
            })
    
    flash('All alerts marked as read.', 'success')
    return redirect(url_for('main.alerts'))

@bp.route('/alerts/clear_old', methods=['POST'])
@login_required
def clear_old():
    """Delete all acknowledged alerts (soft delete)."""
    db = get_firestore_service()
    all_alerts = db.get_all_alerts(exclude_deleted=True)
    
    for alert in all_alerts:
        if alert.get('is_acknowledged', False):
            db.delete_alert(alert['id'], permanent=False)
    
    flash('Old alerts cleared.', 'success')
    return redirect(url_for('main.alerts'))

@bp.route('/alerts/mark_read/<alert_id>', methods=['POST'])
@login_required
def mark_read(alert_id):
    db = get_firestore_service()
    
    # Check if alert exists
    alert_doc = db.db.collection('alerts').document(alert_id).get()
    if not alert_doc.exists:
        flash('Alert not found.', 'error')
        return redirect(url_for('main.alerts'))
    
    db.update_alert(alert_id, {'is_acknowledged': True})
    flash('Alert marked as read.', 'success')
    return redirect(url_for('main.alerts'))

@bp.route('/alerts/delete/<alert_id>', methods=['POST'])
@login_required
def delete_alert(alert_id):
    db = get_firestore_service()
    
    # Check if alert exists
    alert_doc = db.db.collection('alerts').document(alert_id).get()
    if not alert_doc.exists:
        flash('Alert not found.', 'error')
        return redirect(url_for('main.alerts'))
    
    db.delete_alert(alert_id, permanent=False)
    flash('Alert moved to Recently Deleted.', 'success')
    return redirect(url_for('main.alerts'))

@bp.route('/recently_deleted')
@login_required
def recently_deleted():
    db = get_firestore_service()
    deleted_alerts = db.get_deleted_alerts()
    return render_template('recently_deleted.html', title='Recently Deleted', alerts=deleted_alerts)

@bp.route('/recently_deleted/restore/<alert_id>', methods=['POST'])
@login_required
def restore_alert(alert_id):
    db = get_firestore_service()
    
    # Check if alert exists
    alert_doc = db.db.collection('alerts').document(alert_id).get()
    if not alert_doc.exists:
        flash('Alert not found.', 'error')
        return redirect(url_for('main.recently_deleted'))
    
    db.restore_alert(alert_id)
    flash('Alert restored.', 'success')
    return redirect(url_for('main.recently_deleted'))

@bp.route('/recently_deleted/delete_permanently/<alert_id>', methods=['POST'])
@login_required
def delete_permanently(alert_id):
    db = get_firestore_service()
    
    # Check if alert exists
    alert_doc = db.db.collection('alerts').document(alert_id).get()
    if not alert_doc.exists:
        flash('Alert not found.', 'error')
        return redirect(url_for('main.recently_deleted'))
    
    db.delete_alert(alert_id, permanent=True)
    flash('Alert permanently deleted.', 'success')
    return redirect(url_for('main.recently_deleted'))

@bp.route('/data_history')
@login_required
def data_history():
    db = get_firestore_service()
    sensor_readings = db.get_sensor_readings(limit=100)
    return render_template('data_history.html', title='Data History', sensor_readings=sensor_readings)

@bp.route('/devices')
@login_required
def devices():
    db = get_firestore_service()
    all_devices = db.get_all_devices()
    return render_template('devices.html', title='Devices', devices=all_devices)

@bp.route('/reports')
@login_required
def reports():
    db = get_firestore_service()
    all_reports = db.get_all_reports(status='active')
    return render_template('reports.html', title='Monitoring Reports', reports=all_reports)

@bp.route('/reports/deleted')
@login_required
def deleted_reports_view():
    db = get_firestore_service()
    deleted = db.get_all_reports(status='deleted')
    return render_template('deleted_reports.html', title='Deleted Reports', reports=deleted)

@bp.route('/reports/delete/<report_id>', methods=['POST'])
@login_required
def delete_report(report_id):
    db = get_firestore_service()
    
    # Check if report exists
    report_doc = db.db.collection('reports').document(report_id).get()
    if not report_doc.exists:
        flash('Report not found.', 'error')
        return redirect(url_for('main.reports'))
    
    db.delete_report(report_id, permanent=False, deleted_by='System Admin')
    flash('Report moved to deleted reports.', 'success')
    return redirect(url_for('main.reports'))

@bp.route('/reports/restore/<report_id>', methods=['POST'])
@login_required
def restore_report(report_id):
    db = get_firestore_service()
    
    # Check if report exists
    report_doc = db.db.collection('reports').document(report_id).get()
    if not report_doc.exists:
        flash('Report not found.', 'error')
        return redirect(url_for('main.deleted_reports_view'))
    
    db.restore_report(report_id)
    flash('Report restored.', 'success')
    return redirect(url_for('main.deleted_reports_view'))

@bp.route('/reports/permanent_delete/<report_id>', methods=['POST'])
@login_required
def delete_report_permanently(report_id):
    db = get_firestore_service()
    
    # Check if report exists
    report_doc = db.db.collection('reports').document(report_id).get()
    if not report_doc.exists:
        flash('Report not found.', 'error')
        return redirect(url_for('main.deleted_reports_view'))
    
    db.delete_report(report_id, permanent=True)
    flash('Report permanently deleted.', 'success')
    return redirect(url_for('main.deleted_reports_view'))
