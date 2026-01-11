from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from app import app, db
from app.models import User, Payslip
from werkzeug.utils import secure_filename
import os


# Route to delete all users except current admin
@app.route('/admin_delete_all_users', methods=['POST'])
@login_required
def admin_delete_all_users():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('index'))
    # Delete all payslips first
    Payslip.query.delete()
    # Delete all users except current admin
    User.query.filter(User.id != current_user.id).delete()
    db.session.commit()
    flash('All users (except current admin) and all payslips have been deleted.')
    return redirect(url_for('admin_dashboard'))

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('employee_dashboard'))
    if request.method == 'POST':
        login_id = request.form['login_id']
        password = request.form['password']
        user = User.query.filter((User.email == login_id) | (User.employee_id == login_id)).first()
        if user is None or not user.check_password(password):
            flash('Invalid Email/Employee ID or password')
            return redirect(url_for('index'))
        login_user(user, remember=True)
        if user.is_admin:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('employee_dashboard'))
    return render_template('index.html')



@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/employee_dashboard')
@login_required
def employee_dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    payslips = current_user.payslips.all()
    return render_template('employee_dashboard.html', payslips=payslips)


# User profile page
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('employee_dashboard'))
    employees = User.query.filter_by(is_admin=False).all()
    all_users = User.query.all()
    # Gather payslips for all employees
    employee_payslips = {}
    for emp in employees:
        employee_payslips[emp] = emp.payslips.order_by(Payslip.upload_date.desc()).all()
    return render_template('admin_dashboard.html', employees=employees, employee_payslips=employee_payslips, all_users=all_users)

@app.route('/upload_payslip', methods=['POST'])
@login_required
def upload_payslip():
    if not current_user.is_admin:
        return redirect(url_for('employee_dashboard'))
    
    employee_id = request.form['employee_id']
    month_year = request.form['month_year']
    file = request.files['payslip']
    
    if file:
        filename = secure_filename(file.filename)
        payslip_dir = os.path.join(app.root_path, 'static/payslips', employee_id)
        os.makedirs(payslip_dir, exist_ok=True)
        file_path = os.path.join(payslip_dir, filename)
        file.save(file_path)
        
        payslip = Payslip(user_id=employee_id, file_path=f'payslips/{employee_id}/{filename}', month_year=month_year)
        db.session.add(payslip)
        db.session.commit()
        flash('Payslip uploaded successfully')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        employee_id = request.form['employee_id']
        email = request.form['email']
        phone_number = request.form.get('phone_number', '')
        password = request.form['password']
        is_admin = 'is_admin' in request.form

        existing_employee = User.query.filter_by(employee_id=employee_id).first()
        if existing_employee:
            flash('Employee ID already exists. Please use a different one.')
            return redirect(url_for('create_user'))

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already exists. Please use a different email.')
            return redirect(url_for('create_user'))

        user = User(first_name=first_name, last_name=last_name, employee_id=employee_id, email=email, phone_number=phone_number, is_admin=is_admin)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('User created successfully')
        return redirect(url_for('index'))
    return render_template('create_user.html')

# Admin Reset Password (admin can reset any user's password)
@app.route('/admin_reset_password/<int:user_id>', methods=['POST'])
@login_required
def admin_reset_password(user_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    user = User.query.get(user_id)
    if not user:
        flash('User not found.')
        return redirect(url_for('admin_dashboard'))
    
    new_password = request.form['new_password']
    user.set_password(new_password)
    db.session.commit()
    flash(f'Password reset successfully for user {user.username}.')
    return redirect(url_for('admin_dashboard'))

# Admin Delete User
@app.route('/admin_delete_user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    user = User.query.get(user_id)
    if not user:
        flash('User not found.')
        return redirect(url_for('admin_dashboard'))
    
    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        flash('You cannot delete your own account.')
        return redirect(url_for('admin_dashboard'))
    
    username = user.username
    # Delete associated payslips first
    Payslip.query.filter_by(user_id=user.id).delete()
    # Delete the user
    db.session.delete(user)
    db.session.commit()
    flash(f'User {username} and all associated data have been deleted successfully.')
    return redirect(url_for('admin_dashboard'))

