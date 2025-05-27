from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST, require_GET
from .models import UserLog, Rice, Users, CustomerOrder
from django.http import HttpResponseBadRequest


@require_POST
def undo_update(request, log_id):
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return HttpResponseBadRequest("Invalid request method.")
    log = get_object_or_404(UserLog, id=log_id)

    # Only allow undo for add_stock actions
    if not (log.action_type.startswith('Added') and 'sacks to' in log.action_type):
        return JsonResponse({'status': 'error', 'message': 'Undo not allowed for this action.'}, status=400)

    try:
        parts = log.action_type.split()
        quantity = int(parts[1])
        rice_type = ' '.join(parts[4:])
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Malformed log entry.'}, status=400)

    # Try to match rice_type exactly, fallback to case-insensitive match if not found
    rice = Rice.objects.filter(rice_type=rice_type).first()
    if not rice:
        rice = Rice.objects.filter(rice_type__iexact=rice_type.strip()).first()
    if not rice:
        rice_type_clean = rice_type.replace('(Undone)', '').strip()
        rice = Rice.objects.filter(rice_type=rice_type_clean).first() or Rice.objects.filter(rice_type__iexact=rice_type_clean).first()

    if not rice:
        return JsonResponse({'status': 'error', 'message': f'Rice type not found: {rice_type}.'}, status=404)

    # Prevent double-undo
    if getattr(log, 'undone', False):
        return JsonResponse({'status': 'error', 'message': 'Already undone.'}, status=400)

    # Subtract the added stock
    rice.stock_in = max(0, rice.stock_in - quantity)
    rice.current_stock = rice.stock_in - rice.stock_out
    rice.save()

    # Mark log as undone (consider adding a BooleanField 'undone' to UserLog for persistence)
    log.action_type += ' (Undone)'
    log.undone = True  # Make sure your model has this field!
    log.save()

    return JsonResponse({'status': 'success', 'message': 'Stock undo successful.'})


@require_GET
def get_customer_details(request):
    """
    AJAX endpoint: Return customer details and recent order history for autofill.
    Expects ?customer_id=...
    """
    customer_id = request.GET.get('customer_id')
    if not customer_id:
        return JsonResponse({'status': 'error', 'message': 'No customer_id provided.'}, status=400)

    try:
        customer = Users.objects.get(UserID=customer_id, Acc_Status='active')
    except Users.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Customer not found.'}, status=404)

    data = {
        'first_name': customer.name.first_name if customer.name else '',
        'middle_name': customer.name.middle_name if customer.name else '',
        'last_name': customer.name.last_name if customer.name else '',
        'suffix': customer.name.suffix if customer.name else '',
        'house_no': customer.address.house_unit_number if customer.address else '',
        'street': customer.address.street_name if customer.address else '',
        'barangay': customer.address.barangay if customer.address else '',
        'city': customer.address.city_municipality if customer.address else '',
        'customer_mobile_number': '',
        'receiver_mobile_number': '',
        'order_history': []
    }

    last_order = CustomerOrder.objects.filter(customer=customer).order_by('-created_at').first()
    if last_order:
        data['customer_mobile_number'] = last_order.customer_mobile_number or ''
        data['receiver_mobile_number'] = last_order.receiver_mobile_number or ''

    orders = CustomerOrder.objects.filter(customer=customer).order_by('-created_at')[:5]
    data['order_history'] = [
        {
            'date': o.created_at.strftime('%Y-%m-%d %H:%M'),
            'rice_type': o.rice_type.rice_type if o.rice_type else '',
            'quantity': o.quantity,
            'total_cost': o.total_cost,
            'status': o.approval_status,
            'delivery_status': o.delivery_status if hasattr(o, 'delivery_status') else ''
        }
        for o in orders
    ]

    return JsonResponse({'status': 'success', 'data': data})


import json
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from .models import UserName, UserAddress
from django.http import JsonResponse
from django.contrib import messages
from django.db import connection
from django.db.models import Case, When, Value, Sum, Q, CharField, BooleanField
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Users, Rice, CustomerOrder
from .models import Employee
import json
import random

from django.shortcuts import render, redirect
from django.db import connection
from .models import Employee  # Make sure this model is correctly defined in models.py

from django.shortcuts import render
from .models import Announcement, Users  # assuming your model is named Announcement and employee table is Users


from django.shortcuts import render, redirect
from django.db import connection
from webapp.models import Employee
from django.contrib.auth.hashers import check_password  # For password hashing

def home(request):
    # Redirect if already logged in
    if request.session.get('user_id'):
        role = request.session.get('user_role', '').lower()
        if role == 'user':
            return redirect('user_dashboard')
        elif role in ['admin', 'cashier', 'employee']:
            return redirect('dashboard')
        return render(request, 'login.html', {'error': 'Role not recognized'})

    # Handle login POST
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            return render(request, 'login.html', {'error': 'Please enter both username and password'})

        # Try Employee authentication
        try:
            employee = Employee.objects.get(Username=username)

            # Compare password (plaintext or hashed depending on your setup)
            if employee.Password != password:
                raise ValueError("Invalid credentials")

            if employee.Account_Status.lower() != 'active':
                return render(request, 'login.html', {
                    'error': 'Your account is inactive. Please contact the administrator.'
                })

            full_name = f"{employee.FirstName} {employee.MiddleName or ''} {employee.LastName} {employee.Suffix or ''}".strip()
            role = employee.Role.strip().lower()

            # Set session
            request.session['user_id'] = employee.EmployeeID
            request.session['employee_id'] = employee.EmployeeID
            request.session['user_name'] = full_name
            request.session['user_role'] = role

            # Redirect by role
            if role == 'user':
                return redirect('user_dashboard')
            elif role in ['admin', 'cashier', 'employee']:
                return redirect('dashboard')
            else:
                return render(request, 'login.html', {'error': 'Role not recognized'})

        except Employee.DoesNotExist:
            pass
        except ValueError:
            return render(request, 'login.html', {'error': 'Invalid username or password'})

        # Fallback: Try Users table
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT u.UserID, n.first_name, n.middle_name, n.last_name, n.suffix,
                       u.Role, u.Password, u.Acc_Status
                FROM webapp_users u
                LEFT JOIN user_name n ON u.name_id = n.id
                WHERE u.Username = %s
            """, [username])
            row = cursor.fetchone()

        if not row:
            return render(request, 'login.html', {'error': 'Invalid username or password'})

        user_id, first, middle, last, suffix, role, db_password, status = row


        if not check_password(password, db_password):
            return render(request, 'login.html', {'error': 'Invalid username or password'})

        if status.lower() != 'active':
            return render(request, 'login.html', {
                'error': 'Your account is inactive. Please contact the administrator.'
            })

        full_name = f"{first} {middle or ''} {last} {suffix or ''}".strip()
        role = role.strip().lower()

        # Set session
        request.session['user_id'] = user_id
        request.session['user_name'] = full_name
        request.session['user_role'] = role

        # Redirect by role
        if role == 'user':
            return redirect('user_dashboard')
        elif role in ['admin', 'cashier', 'employee']:
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': 'Role not recognized'})

    # Default: show login form
    return render(request, 'login.html')



from django.utils.timezone import now
from django.contrib import messages
from .models import Announcement, Employee

def add_announcement(request):
    if request.method == 'POST':
        message = request.POST.get('message')
        created_by_id = request.session.get('employee_id')  # Set during login

        if message and created_by_id:
            try:
                Announcement.objects.create(
                    message=message,
                    created_by_id=created_by_id,
                    created_at=now()
                )
                messages.success(request, 'Announcement added!')
            except Exception as e:
                messages.error(request, f'Error adding announcement: {str(e)}')
        else:
            if not message:
                messages.error(request, 'Message is required.')
            if not created_by_id:
                messages.error(request, 'You are not logged in properly (missing employee ID).')

        return redirect('dashboard')

    return redirect('dashboard')


from django.shortcuts import render
from django.db.models import Sum
from datetime import date
from django.utils.timezone import now
from .models import Rice, CustomerOrder, Supplier, Users, Announcement, Employee

from pytz import timezone
PH_TZ = timezone('Asia/Manila')


def dashboard_view(request):
    is_admin = False
    role = None
    employee_id = None

    if request.user.is_authenticated:
        try:
            custom_user = Users.objects.get(Username=request.user.username)
            employee_id = custom_user.EmployeeID
            role = custom_user.Role.strip().lower()
            is_admin = (role == 'admin')
        except Users.DoesNotExist:
            pass


    from .models import Stock
    stock_data = Stock.objects.select_related('rice_type').all()

    recent_sales = CustomerOrder.objects.filter(approval_status='Approved') \
        .select_related('rice_type') \
        .order_by('-created_at')[:5]

    total_sales_today = CustomerOrder.objects.filter(
        created_at__date=date.today(),
        approval_status='Approved'
    ).aggregate(total_sales=Sum('amount_paid'))['total_sales'] or 0

    stock_out_count = stock_data.filter(current_stock=0).count()
    low_stock_count = stock_data.filter(current_stock__lte=100).exclude(current_stock=0).count()
    total_rice_types = stock_data.values('rice_type').distinct().count()

    notifications = []
    read_notifications = request.session.get('read_notifications', [])
    current_timestamp = now().astimezone(PH_TZ)

    if is_admin:
        pending_suppliers_count = Supplier.objects.filter(approval_status='Pending').count()
        if pending_suppliers_count > 0:
            notif_id = f'supplier_{pending_suppliers_count}'
            if notif_id not in read_notifications:
                notifications.append({
                    "id": notif_id,
                    "message": f"{pending_suppliers_count} pending supplier order(s) need approval",
                    "timestamp": current_timestamp,
                })

        pending_orders_count = CustomerOrder.objects.filter(approval_status__iexact='Pending').count()
        if pending_orders_count > 0:
            notif_id = f'orders_{pending_orders_count}'
            if notif_id not in read_notifications:
                notifications.append({
                    "id": notif_id,
                    "message": f"{pending_orders_count} pending customer order(s) need approval",
                    "timestamp": current_timestamp,
                })

    for item in stock_data.filter(current_stock=0):
        notif_id = f'outofstock_{item.stockID}'
        if notif_id not in read_notifications:
            notifications.append({
                "id": notif_id,
                "message": f"{item.rice_type.rice_type} ({item.packaging}) is out of stock!",
                "timestamp": current_timestamp,
            })

    for item in stock_data.filter(current_stock__lte=100).exclude(current_stock=0):
        notif_id = f'lowstock_{item.stockID}'
        if notif_id not in read_notifications:
            notifications.append({
                "id": notif_id,
                "message": f"{item.rice_type.rice_type} ({item.packaging}) is running low (only {item.current_stock} sacks left)",
                "timestamp": current_timestamp,
            })

    announcements = Announcement.objects.select_related('created_by') \
        .order_by('-created_at')[:10]

    return render(request, "dashboard.html", {
        'stock_data': stock_data,
        'recent_sales': recent_sales,
        'total_sales_today': total_sales_today,
        'stock_out_today': stock_out_count,
        'low_stock_warnings': low_stock_count,
        'total_rice_types': total_rice_types,
        'notifications': notifications,
        'is_admin': is_admin,
        'role': role,
        'employee_id': employee_id,
        'announcements': announcements,
    })

from django.shortcuts import get_object_or_404, redirect
from django.utils.timezone import now
from django.contrib import messages

def edit_announcement(request, announcement_id):
    announcement = get_object_or_404(Announcement, pk=announcement_id)

    logged_in_employee_id = request.session.get('user_id')
    user_role = request.session.get('user_role', '').lower()

    if not logged_in_employee_id:
        messages.error(request, "You must be logged in to edit announcements.")
        return redirect('dashboard')

    if announcement.created_by_id != logged_in_employee_id and user_role != 'admin':
        messages.error(request, "You don't have permission to edit this announcement.")
        return redirect('dashboard')

    if request.method == 'POST':
        new_message = request.POST.get('message', '').strip()
        if not new_message:
            messages.error(request, "Message cannot be empty.")
            return redirect('dashboard')
        try:
            announcement.message = new_message
            announcement.created_at = now()
            announcement.save()
            messages.success(request, "Announcement updated successfully.")
        except Exception as e:
            messages.error(request, f"An error occurred while updating the announcement: {str(e)}")
        return redirect('dashboard')

    # Render the edit form for GET requests
    return render(request, 'edit_announcement.html', {'announcement': announcement})

@require_POST
def delete_announcement(request, announcement_id):
    try:
        announcement = get_object_or_404(Announcement, pk=announcement_id)
        announcement.delete()
        return JsonResponse({'status': 'success', 'message': 'Announcement deleted.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error deleting announcement: {str(e)}'})

def permanent_delete_user(request, employee_id):
    if request.method == 'POST':
        user = get_object_or_404(Employee, EmployeeID=employee_id)
        user.delete()
        messages.success(request, "User permanently deleted.")
    return redirect('edituser')  # or your user list page

def toggle_notification(request):
    notif_id = request.POST.get('id')
    read_notifications = request.session.get('read_notifications', [])
    if notif_id:
        if notif_id in read_notifications:
            read_notifications.remove(notif_id)
        else:
            read_notifications.append(notif_id)
        request.session['read_notifications'] = read_notifications
    return JsonResponse({'status': 'ok'})

from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import UserName, UserAddress, Users  # adjust imports based on your structure

@require_POST
def add_customer(request):
    try:
        # Create name record
        name = UserName.objects.create(
            first_name=request.POST.get('first_name'),
            middle_name=request.POST.get('middle_name'),
            last_name=request.POST.get('last_name'),
            suffix=request.POST.get('suffix')
        )

        # Generate Username from full name (e.g., 'JuanDelaCruz')
        full_name_username = ''.join(filter(None, [
            name.first_name,
            name.middle_name or '',
            name.last_name,
            name.suffix or ''
        ])).replace(' ', '')

        # Create address record
        address = UserAddress.objects.create(
            house_unit_number=request.POST.get('house_no'),
            street_name=request.POST.get('street'),
            barangay=request.POST.get('barangay'),
            city_municipality=request.POST.get('city'),
            province=request.POST.get('province') or '',
            zip_code=request.POST.get('zip_code') or '',
        )

        # Save to Users table (using name and address foreign keys)
        Users.objects.create(
            name=name,
            address=address,
            Username=full_name_username,
            Customer_Mobile_Number=request.POST.get('customer_mobile_number'),
            Receiver_Mobile_Number=request.POST.get('receiver_mobile_number')  # if you have this field
        )

        return JsonResponse({'status': 'success', 'message': 'Customer added successfully.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import UserName, UserAddress, Users

@require_POST
def add_customer(request):
    try:
        # Create UserName instance
        name = UserName.objects.create(
            first_name=request.POST.get('first_name'),
            middle_name=request.POST.get('middle_name'),
            last_name=request.POST.get('last_name'),
            suffix=request.POST.get('suffix'),
        )

        # Create UserAddress instance
        address = UserAddress.objects.create(
            house_unit_number=request.POST.get('house_no'),
            street_name=request.POST.get('street'),
            barangay=request.POST.get('barangay'),
            city_municipality=request.POST.get('city'),
            province='Not specified',  # Provide a default or fetch from request.POST if needed
            zip_code='0000'  # Provide a default or fetch from request.POST if needed
        )

        # Create Users instance
        Users.objects.create(
            name=name,
            address=address,
            Customer_Mobile_Number=request.POST.get('customer_mobile_number')
        )

        return JsonResponse({'status': 'success', 'message': 'Customer added successfully.'})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})



from decimal import Decimal, InvalidOperation
from .models import Rice, CustomerOrder, Users, UserName, UserAddress, Employee

def new_sale_view(request):
    if request.method == 'POST':
        try:
            # 1. Validate rice type
            rice_type_id = request.POST.get('rice-type')
            if not rice_type_id:
                return JsonResponse({'status': 'error', 'message': 'Please select a rice type.'})

            # 2. Validate customer name
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            if not first_name or not last_name:
                return JsonResponse({'status': 'error', 'message': 'Customer first and last name are required.'})

            middle_name = request.POST.get('middle_name', '')
            suffix = request.POST.get('suffix', '')

            # 3. Get or create UserName instance
            user_name, _ = UserName.objects.get_or_create(
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                middle_name=middle_name.strip() if middle_name else None,
                suffix=suffix.strip() if suffix else None
            )

            # 4. Get or create UserAddress instance
            address_fields = {
                'house_unit_number': request.POST.get('house_unit_number', ''),
                'building_name': request.POST.get('building_name', ''),
                'street_name': request.POST.get('street_name', ''),
                'barangay': request.POST.get('barangay', ''),
                'city_municipality': request.POST.get('city_municipality', ''),
                'province': request.POST.get('province', ''),
                'zip_code': request.POST.get('zip_code', ''),
            }
            user_address, _ = UserAddress.objects.get_or_create(**address_fields)

            # 5. Get or create Users instance
            customer, _ = Users.objects.get_or_create(
                name=user_name,
                defaults={
                    'address': user_address,
                    'Customer_Mobile_Number': request.POST.get('customer_contact', ''),
                }
            )

            # 6. Get Rice object
            try:
                rice = Rice.objects.get(riceID=rice_type_id)
            except Rice.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Selected rice type does not exist.'})

            # 7. Get employee
            employee = None
            employee_id = request.POST.get('employee_id')
            if employee_id:
                employee = Employee.objects.filter(EmployeeID=employee_id).first()

            # 8. Parse numeric fields
            try:
                quantity = int(request.POST.get('quantity', 0))
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Invalid quantity.'})

            def parse_decimal(value, field):
                try:
                    return Decimal(str(value))
                except (InvalidOperation, TypeError, ValueError):
                    raise ValueError(f"Invalid {field}.")

            try:
                cost_per_sack = parse_decimal(request.POST.get('cost_per_sack', '0'), 'cost per sack')
                total_cost = parse_decimal(request.POST.get('total_cost', '0'), 'total cost')
                amount_paid = parse_decimal(request.POST.get('amount_paid', '0'), 'amount paid')
                amount_change = parse_decimal(request.POST.get('amount_change', '0'), 'amount change')
            except ValueError as e:
                return JsonResponse({'status': 'error', 'message': str(e)})

            # 9. Create CustomerOrder
            CustomerOrder.objects.create(
                customer=customer,
                rice_type=rice,
                quantity=quantity,
                cost_per_sack=cost_per_sack,
                total_cost=total_cost,
                payment_method=request.POST.get('payment_method', ''),
                amount_paid=amount_paid,
                amount_change=amount_change,
                delivery_type=request.POST.get('delivery_type', 'delivery'),
                delivery_status='Pending',
                approval_status='Pending',
                employee=employee,
            )

            return redirect('view_sales_history')

        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred. Please try again.'})

    # GET method - display form
    rice_data = Rice.objects.all()
    cashier_admin_users = Employee.objects.filter(Role__in=['Cashier', 'Admin'], Account_Status='active')
    customer_users = Users.objects.filter(name__isnull=False)  # optional filter

    return render(request, 'sales_transaction.html', {
        'rice_data': rice_data,
        'rice_list': rice_data,
        'cashier_admin_users': cashier_admin_users,
        'customer_users': customer_users
    })


def view_sales_report(request):
    return render(request, 'view_sales_report.html')

def inventory_turnover(request):
    return render(request, 'Inventory_Turnover_Report.html')


from django.shortcuts import render
from .models import Supplier

def supplier(request):
    suppliers = Supplier.objects.all()
    print(suppliers)  
    
    context = {
        'suppliers': suppliers
    }
    return render(request, 'Supplier.html', context)



from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
import json

from .models import Rice, Stock

@csrf_exempt  # Optional: Use only if CSRF tokens are not being sent
@require_POST
def updatestock(request, riceID):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    price_per_sack = data.get('price_per_sack')
    description = data.get('description', '')
    packaging = data.get('packaging', '50kg')  # You may allow the frontend to send this

    if price_per_sack is None:
        return JsonResponse({'status': 'error', 'message': 'Price per sack is required'}, status=400)

    try:
        price_per_sack = float(price_per_sack)
        if price_per_sack < 0:
            raise ValueError()
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Invalid price per sack'}, status=400)

    # Get Rice and Stock object
    rice = get_object_or_404(Rice, riceID=riceID)

    # Get the correct Stock entry for this Rice and Packaging
    stock = get_object_or_404(Stock, rice_type=rice, packaging=packaging)

    # Update values
    stock.price_per_sack = price_per_sack
    stock.save()

    # Optionally update the description in the Rice table
    rice.description = description
    rice.save()

    return JsonResponse({'status': 'success', 'message': 'Stock and description updated successfully'})


def removestock(request):
    return render(request, 'removestock.html')

def viewstocklevel(request):
    rice_data = Rice.objects.all()
    return render(request, "viewstocklevel.html", {
        'stock_data': rice_data
    })

def logout_view(request):
    request.session.flush()
    return redirect('http://127.0.0.1:8000/')

from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Employee  # Adjust import according to your app structure

def adduser(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        middle_name = request.POST.get('middle_name')  # optional
        last_name = request.POST.get('last_name')
        suffix = request.POST.get('suffix')  # optional
        role = request.POST.get('role')

        # Basic validation example (you can expand this)
        if not (username and password and first_name and last_name and role):
            messages.error(request, "Please fill in all required fields.")
            return redirect('add_user')

        new_employee = Employee(
            Username=username,
            Password=password,
            FirstName=first_name,
            MiddleName=middle_name,
            LastName=last_name,
            Suffix=suffix,
            Role=role,
            Account_Status='inactive'
        )
        new_employee.save()

        messages.success(request, 'User added successfully!')
        return redirect('add_user')

    return render(request, 'adduser.html')


def delete_user(request, EmployeeID):
    user = get_object_or_404(Employee, EmployeeID=EmployeeID)
    user.Account_Status = 'deleted'  # Updated field name
    user.save()
    messages.success(request, f'User {user.Username} marked as deleted.')
    return redirect('edituser')



def restore_user(request, employee_id):
    user = get_object_or_404(Employee, EmployeeID=employee_id)
    user.Account_Status = 'active'  # Correct field name from your table
    user.save()
    messages.success(request, f'User {user.Username} restored.')
    return redirect('edituser')


from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from .models import Employee  # assuming your Django model is named Employee

def edituser(request, EmployeeID=None):
    search_query = request.GET.get('search', '')

    # Active users excluding soft-deleted ones (Account_Status != 'deleted')
    if search_query:
        all_users = Employee.objects.filter(
            (Q(FirstName__icontains=search_query) | Q(LastName__icontains=search_query) | Q(Username__icontains=search_query)) &
            ~Q(Account_Status='deleted')
        )
    else:
        all_users = Employee.objects.exclude(Account_Status='deleted')

    # Soft-deleted users
    deleted_users = Employee.objects.filter(Account_Status='deleted')

    selected_user = None
    success_message = None

    if EmployeeID:
        selected_user = get_object_or_404(Employee, EmployeeID=EmployeeID)

        if request.method == "POST":
            selected_user.FirstName = request.POST.get("FirstName")
            selected_user.MiddleName = request.POST.get("MiddleName")
            selected_user.LastName = request.POST.get("LastName")
            selected_user.Suffix = request.POST.get("Suffix")
            selected_user.Role = request.POST.get("Role")
            selected_user.Username = request.POST.get("Username")
            selected_user.Password = request.POST.get("Password")
            selected_user.Account_Status = request.POST.get("Account_Status")
            selected_user.save()

            success_message = "User updated successfully!"
            return redirect('edituser', EmployeeID=EmployeeID)

    context = {
        'users': all_users,
        'deleted_users': deleted_users,
        'selected_user': selected_user,
        'success_message': success_message,
    }
    return render(request, "edituser.html", context)


def profile(request):
    user_id = request.session.get('user_id') 

    if not user_id:
        return redirect('login')  
    
    if request.method == 'POST':
        # Assuming you want to update these fields separately
        first_name = request.POST.get('FirstName')
        middle_name = request.POST.get('MiddleName')
        last_name = request.POST.get('LastName')
        suffix = request.POST.get('Suffix')
        username = request.POST.get('Username')
        password = request.POST.get('Password')

        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE employee SET 
                    FirstName = %s, 
                    MiddleName = %s, 
                    LastName = %s, 
                    Suffix = %s,
                    Username = %s, 
                    Password = %s
                WHERE EmployeeID = %s
            """, [first_name, middle_name, last_name, suffix, username, password, user_id])

        return redirect('profile')

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT FirstName, MiddleName, LastName, Suffix, Username, Role, Account_Status, Password
            FROM employee 
            WHERE EmployeeID = %s
        """, [user_id])
        row = cursor.fetchone()

    if not row:
        return redirect('login') 

    user = {
        'FirstName': row[0],
        'MiddleName': row[1],
        'LastName': row[2],
        'Suffix': row[3],
        'Username': row[4],
        'Role': row[5],
        'Account_Status': row[6],
        'Password': row[7],
    }

    return render(request, 'profile.html', {'user': user})


def log_user_action(employee_id, action_type):
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO user_logs (employee_id, action_type, timestamp)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
        """, [employee_id, action_type])


from django.shortcuts import render, redirect
from .models import Rice, Stock, UserLog, Users
from django.utils import timezone

def addstock(request):
    if request.method == "POST":
        rice_type_id = request.POST.get("riceType")
        quantity = request.POST.get("quantity")
        packaging = request.POST.get("packaging", "50kg")  # default to 50kg
        employee_id = request.session.get('employee_id')

        if not rice_type_id or not quantity:
            return render(request, 'addstock.html', {
                'rice_data': Rice.objects.all(),
                'stock_data': Stock.objects.select_related('rice_type').all(),
                'error': 'All fields are required.'
            })

        try:
            rice = Rice.objects.get(riceID=rice_type_id)
        except Rice.DoesNotExist:
            return render(request, 'addstock.html', {
                'rice_data': Rice.objects.all(),
                'stock_data': Stock.objects.select_related('rice_type').all(),
                'error': 'Selected rice type does not exist.'
            })

        try:
            quantity_int = int(quantity)
            if quantity_int <= 0:
                raise ValueError
        except ValueError:
            return render(request, 'addstock.html', {
                'rice_data': Rice.objects.all(),
                'stock_data': Stock.objects.select_related('rice_type').all(),
                'error': 'Quantity must be a positive integer.'
            })

        # Get or create stock record
        stock_obj, created = Stock.objects.get_or_create(
            rice_type=rice,
            packaging=packaging,
            defaults={'stock_in': 0, 'stock_out': 0, 'price_per_sack': 0}
        )

        # Update stock_in
        stock_obj.stock_in += quantity_int
        stock_obj.save()  # This also updates current_stock

        # ✅ Record log if employee is logged in
        if employee_id:
            try:
                user = Users.objects.get(pk=employee_id)
                action = f"Added {quantity_int} sacks to {rice.rice_type} ({packaging})"
                UserLog.objects.create(user=user, action_type=action, timestamp=timezone.now())
            except Users.DoesNotExist:
                pass  # Optionally handle this case if needed

        return redirect('addstock')

    # Show logs
    logs = UserLog.objects.order_by('-timestamp')[:20]
    update_logs = []
    for log in logs:
        if log.action_type.startswith('Added') and 'sacks to' in log.action_type:
            try:
                parts = log.action_type.split()
                quantity = int(parts[1])
                rice_type = ' '.join(parts[4:])
            except Exception:
                quantity = None
                rice_type = log.action_type
            undone = '(Undone)' in log.action_type
            update_logs.append({
                'id': log.id,
                'action': 'add_stock',
                'quantity_added': quantity,
                'rice_type': rice_type,
                'timestamp': log.timestamp,
                'undone': undone,
            })

    return render(request, 'addstock.html', {
        'rice_data': Rice.objects.all(),
        'stock_data': Stock.objects.select_related('rice_type').all(),
        'update_logs': update_logs,
    })





from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db import connection
from webapp.models import Rice, Stock 
# views.py
def deletestock(request, stock_id):
    if request.method == 'POST':
        try:
            stock = get_object_or_404(Stock, stockID=stock_id)
            stock.delete()
            messages.success(request, "Stock deleted successfully.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
    else:
        messages.error(request, "Invalid request method.")
    return redirect('addstock')

def view_stock_levels(request):
    
    rice_data = Rice.objects.all()
    return render(request, 'viewstocklevel.html', {'rice_data': rice_data})

import json
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
from .models import Rice

from decimal import Decimal, InvalidOperation
import json
from django.http import JsonResponse
from .models import Rice

from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
from .models import Rice, Stock
import json

def add_rice(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rice_type = data.get('rice_type')
            price_per_sack = data.get('price_per_sack')
            description = data.get('description', '')  # Optional field
            packaging = data.get('packaging', '50kg')  # Default packaging

            if not rice_type or price_per_sack is None:
                return JsonResponse({'status': 'error', 'message': 'Rice type and price are required'})

            # Convert price_per_sack to Decimal safely
            try:
                price = Decimal(price_per_sack)
                if price <= 0:
                    raise InvalidOperation
            except (InvalidOperation, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Price per sack must be a positive decimal number'})

            # Check if rice type already exists
            if Rice.objects.filter(rice_type__iexact=rice_type).exists():
                return JsonResponse({'status': 'error', 'message': 'Rice type already exists'})

            # Create new Rice object
            new_rice = Rice.objects.create(
                rice_type=rice_type,
                description=description
            )

            # Create corresponding Stock entry with default 0 stock
            stock = Stock.objects.create(
                rice_type=new_rice,
                packaging=packaging,
                price_per_sack=price,
                stock_in=0,
                stock_out=0
            )

            # Prepare response data
            response_data = {
                'riceID': new_rice.riceID,
                'rice_type': new_rice.rice_type,
                'description': new_rice.description,
                'packaging': stock.packaging,
                'price_per_sack': str(stock.price_per_sack),
                'stock_in': stock.stock_in,
                'stock_out': stock.stock_out,
                'current_stock': stock.current_stock,
            }

            return JsonResponse({
                'status': 'success',
                'message': 'Rice type added successfully',
                'data': response_data
            })

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


from django.http import JsonResponse
from webapp.models import Users

def get_customer_details(request):
    customer_id = request.GET.get('customer_id')
    if not customer_id:
        return JsonResponse({'status': 'error', 'message': 'No customer ID provided.'})

    try:
        customer = Users.objects.get(UserID=customer_id)
    except Users.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Customer not found.'})

    # Build address string or fields
    address = {
        'house_no': getattr(customer, 'house_no', ''),
        'street': getattr(customer, 'street', ''),
        'barangay': getattr(customer, 'barangay', ''),
        'city': getattr(customer, 'city', ''),
        'province': getattr(customer, 'province', ''),
        'zip_code': getattr(customer, 'zip_code', ''),
    }

    data = {
        'first_name': customer.first_name if hasattr(customer, 'first_name') else '',
        'middle_name': getattr(customer, 'middle_name', ''),
        'last_name': customer.last_name if hasattr(customer, 'last_name') else '',
        'suffix': getattr(customer, 'suffix', ''),
        'house_no': address['house_no'],
        'street': address['street'],
        'barangay': address['barangay'],
        'city': address['city'],
        'province': address['province'],
        'zip_code': address['zip_code'],
        'customer_mobile_number': getattr(customer, 'mobile_number', ''),
        'receiver_mobile_number': getattr(customer, 'receiver_mobile_number', ''),
        # add other fields as needed
    }

    return JsonResponse({'status': 'success', 'data': data})


from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from webapp.models import CustomerOrder, Rice, Employee, Users

@require_POST
@csrf_protect
def process_order(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

    # Get POST data
    rice_type_id = request.POST.get("rice_type_id")
    customer_id = request.POST.get("customer_id")

    # Validation for required fields
    if not rice_type_id:
        return JsonResponse({'status': 'error', 'message': 'Please select a rice type.'})
    if not customer_id:
        return JsonResponse({'status': 'error', 'message': 'Customer ID is required.'})

    # Get rice object
    try:
        rice = Rice.objects.get(riceID=rice_type_id)
    except Rice.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Selected rice type does not exist.'})

    # Get customer object
    try:
        customer = Users.objects.get(UserID=customer_id)
    except Users.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Customer not found.'})

    # Optional: get employee
    employee = None
    employee_id = request.POST.get('employee_id')
    if employee_id:
        try:
            employee = Users.objects.get(UserID=employee_id, Role='employee')  # Assuming employee is also in Users table
        except Users.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Employee not found.'})

    # Generate delivery address from customer if available
    delivery_address = ""
    if hasattr(customer, 'address') and customer.address:
        addr = customer.address
        delivery_address = f"{addr.house_unit_number or ''} {addr.building_name or ''} {addr.street_name or ''}, {addr.barangay or ''}, {addr.city_municipality or ''}, {addr.province or ''} {addr.zip_code or ''}".strip()

    # Safely parse numeric input
    try:
        quantity = int(request.POST.get('quantity', 0))
        cost_per_sack = Decimal(str(request.POST.get('cost_per_sack', '0')))
        total_cost = Decimal(str(request.POST.get('total_cost', '0')))
        amount_paid = Decimal(str(request.POST.get('amount_paid', '0')))
        amount_change = Decimal(str(request.POST.get('amount_change', '0')))
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Invalid numeric input. Please check the amounts and try again.'})

    # Create the order
    try:
        order = CustomerOrder.objects.create(
            customer=customer,
            rice_type=rice,
            quantity=quantity,
            cost_per_sack=cost_per_sack,
            total_cost=total_cost,
            payment_method=request.POST.get('payment_method'),
            amount_paid=amount_paid,
            amount_change=amount_change,
            delivery_type=request.POST.get('delivery_type', 'delivery'),
            delivery_status=request.POST.get('delivery_status', 'Pending'),
            approval_status=request.POST.get('approval_status', 'Pending'),
            employee=employee,
            receiver_name=request.POST.get('receiver_name', ''),
            receiver_mobile_number=request.POST.get('receiver_mobile_number', ''),
            delivery_address=delivery_address,
            order_notes=request.POST.get('order_notes', ''),
        )

        return JsonResponse({'status': 'success', 'message': 'Order created successfully.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f"Order creation failed: {str(e)}"})

from django.core.paginator import Paginator

def customer_orders_view(request):
    customer_orders_qs = CustomerOrder.objects.annotate(
        needs_approval=Case(
            When(approval_status='Pending', then=True),
            default=False,
            output_field=BooleanField()
        )
    ).filter(needs_approval=True).order_by('-order_id')

    # Apply pagination: 10 orders per page
    paginator = Paginator(customer_orders_qs, 10)
    page_number = request.GET.get('page')
    customer_orders = paginator.get_page(page_number)  # This becomes a Page object

    pending_order_count = customer_orders_qs.count()

    return render(request, 'orders.html', {
        'customer_orders': customer_orders,
        'pending_order_count': pending_order_count
    })



from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from webapp.models import CustomerOrder  # adjust import if needed


from django.views.decorators.csrf import csrf_exempt
@require_POST
@csrf_protect
def approve_order(request, order_id):
    try:
        order = get_object_or_404(CustomerOrder, order_id=order_id)
        if order.approval_status == 'Approved':
            return JsonResponse({'status': 'already_approved'})

        rice = order.rice_type
        quantity = order.quantity

        # Deduct from current_stock and increment stock_out
        if rice.current_stock is not None and rice.current_stock >= quantity:
            rice.current_stock -= quantity
            rice.stock_out += quantity
            rice.save()
        else:
            return JsonResponse({'status': 'error', 'message': 'Not enough stock to approve this order.'}, status=400)

        order.approval_status = 'Approved'
        order.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# Decline Order
def decline_order(request, order_id):
    order = get_object_or_404(CustomerOrder, order_id=order_id)
    if request.method == 'POST':
        order.approval_status = 'Declined'
        order.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


# views.py
from django.http import JsonResponse
from .models import CustomerOrder

def delete_order(request, order_id):
    order = CustomerOrder.objects.get(order_id=order_id)
    order.status = 'DELETED'
    order.save()
    return JsonResponse({'success': True})



from django.shortcuts import render, get_object_or_404, redirect
from .models import CustomerOrder
from django.views.decorators.csrf import csrf_exempt

@require_POST
@csrf_protect
def edit_order(request, order_id):
        data = json.loads(request.body)

        try:
            order = CustomerOrder.objects.get(order_id=order_id)
            order.customer_name = data["customer_name"]
            order.customer_address = data["customer_address"]
            order.customer_contact = data["customer_contact"]
            order.rice_type = Rice.objects.get(name=data["rice_type"]) 
            order.delivery_type = data["delivery_type"]
            order.quantity = data["quantity"]
            order.cost_per_sack = data["cost_per_sack"]
            order.amount_paid = data["amount_paid"]
            order.save()

            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

from datetime import datetime
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render

from .models import CustomerOrder, Users


def view_sales_history(request):
    cashier_id = request.GET.get('cashier')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    search = request.GET.get('search')

    orders = CustomerOrder.objects.all()

    if cashier_id:
        try:
            cashier_id = int(cashier_id)
            if Users.objects.filter(EmployeeID=cashier_id, Role__in=['cashier', 'admin']).exists():
                orders = orders.filter(employee__EmployeeID=cashier_id)
        except ValueError:
            pass

    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)

    if search:
        orders = orders.filter(
            Q(customer_name__icontains=search) |
            Q(id__icontains=search)
        )

    from .models import Employee, Supplier
    cashiers = Employee.objects.filter(Role__in=['cashier', 'admin'])

    # Fetch all approved supplier orders
    supplier_orders = Supplier.objects.filter(approval_status__iexact='approved').order_by('-purchase_date')

    context = {
        'customer_orders': orders.order_by('-created_at'),
        'cashiers': cashiers,
        'supplier_orders': supplier_orders,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render(request, 'partials/customer_orders_table.html', context).content.decode('utf-8')
        return JsonResponse({'html': html})

    return render(request, 'view_sales_history.html', context)

from django.core.paginator import Paginator
from django.shortcuts import render
from django.db import connection
from datetime import datetime

def user_logs(request):
    # Get filter values
    filter_date = request.GET.get('date')
    filter_time = request.GET.get('time')
    filter_action = request.GET.get('action', '').lower()

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ul.id, ul.action_type, ul.timestamp,
                   CONCAT(e.FirstName, ' ', COALESCE(e.MiddleName, ''), ' ', e.LastName, ' ', COALESCE(e.Suffix, '')) AS employee_name
            FROM user_logs ul
            JOIN employee e ON ul.employee_id = e.EmployeeID
            ORDER BY ul.timestamp DESC
        """)
        logs = cursor.fetchall()

    log_entries = []
    for log in logs:
        timestamp = log[2]

        if isinstance(timestamp, datetime):
            date_str = timestamp.strftime("%Y-%m-%d")
            time_str = timestamp.strftime("%H:%M:%S")
        elif isinstance(timestamp, str):
            try:
                parsed = datetime.fromisoformat(timestamp)
                date_str = parsed.strftime("%Y-%m-%d")
                time_str = parsed.strftime("%H:%M:%S")
            except ValueError:
                date_str = ''
                time_str = ''
        else:
            date_str = ''
            time_str = ''

        log_entries.append({
            'id': log[0],
            'details': log[1],
            'date': date_str,
            'time': time_str,
            'employee_name': log[3].strip(),
        })

    if filter_date:
        log_entries = [log for log in log_entries if log['date'] == filter_date]
    if filter_time:
        log_entries = [log for log in log_entries if log['time'] == filter_time]
    if filter_action:
        log_entries = [log for log in log_entries if filter_action in log['details'].lower() or filter_action in log['employee_name'].lower()]

    paginator = Paginator(log_entries, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'logs.html', {
        'logs': page_obj,
        'page_obj': page_obj
    })



from django.db.models import Sum, F
from datetime import datetime
from .models import CustomerOrder, Users, Rice

def view_sales_report(request):
    group_by = request.GET.get('group_by', 'rice_type')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    filter_conditions = {}
    if start_date:
        filter_conditions['last_updated__gte'] = start_date
    if end_date:
        filter_conditions['last_updated__lte'] = end_date

    if group_by == 'cashier':
        report_data = CustomerOrder.objects.filter(**filter_conditions) \
            .values('employee__full_Name') \
            .annotate(total_quantity=Sum('quantity'), total_revenue=Sum(F('quantity') * F('cost_per_sack'))) \
            .order_by('employee__full_Name')
    else:
        report_data = CustomerOrder.objects.filter(**filter_conditions) \
            .values('rice_type__rice_type') \
            .annotate(total_quantity=Sum('quantity'), total_revenue=Sum(F('quantity') * F('cost_per_sack'))) \
            .order_by('rice_type__rice_type')

    context = {
        'report_data': report_data,
        'group_by': group_by,
    }

    return render(request, 'view_sales_report.html', context)

from django.db.models import Sum
from datetime import datetime

def inventory_turnover_report(request):
    start_date = request.GET.get('start-date')
    end_date = request.GET.get('end-date')

    orders = CustomerOrder.objects.all()

    if start_date and end_date:
        try:
            start_date_parsed = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_parsed = datetime.strptime(end_date, "%Y-%m-%d")
            orders = orders.filter(created_at__date__range=[start_date_parsed, end_date_parsed])
        except ValueError:
            pass  # Ignore invalid dates

    rice_types = Rice.objects.all()
    turnover_data = []

    from .models import Stock
    for rice in rice_types:
        rice_orders = orders.filter(rice_type=rice)
        total_sales = rice_orders.aggregate(total=Sum('quantity'))['total'] or 0

        # Aggregate all stocks for this rice type
        stocks = Stock.objects.filter(rice_type=rice)
        beginning_stock = stocks.aggregate(total=Sum('stock_in'))['total'] or 0
        ending_stock = stocks.aggregate(total=Sum('current_stock'))['total'] or 0
        # Use average price_per_sack for COGS calculation (or latest, or 0 if none)
        price_per_sack = stocks.order_by('-last_updated').first().price_per_sack if stocks.exists() else 0

        # Calculate COGS
        total_cogs = total_sales * float(price_per_sack)

        try:
            average_inventory = (beginning_stock + ending_stock) / 2
            turnover_ratio = (total_cogs / average_inventory) if average_inventory else 0
        except ZeroDivisionError:
            turnover_ratio = 0

        if total_sales > 0:
            turnover_data.append({
                'rice_type': rice.rice_type,
                'beginning_stock': beginning_stock,
                'ending_stock': ending_stock,
                'cogs': round(total_cogs, 2),
                'inventory_turnover_ratio': round(turnover_ratio, 2),
            })

    return render(request, 'inventory_turnover_Report.html', {
        'turnover_data': turnover_data,
        'start_date': start_date,
        'end_date': end_date,
    })


from django.template.loader import render_to_string
from django.db.models import Q

def view_sales_his(request):
    search = request.GET.get('search', '')
    cashier_id = request.GET.get('cashier', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    orders = CustomerOrder.objects.all().select_related('employee', 'rice_type')

    if cashier_id:
        orders = orders.filter(employee_id=cashier_id)

    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)

    if search:
        orders = orders.filter(
            Q(customer_name__icontains=search) |
            Q(id__icontains=search)
        )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('partials/orders_table.html', {'customer_orders': orders})
        return JsonResponse({'html': html})

    cashiers = Users.objects.all()
    return render(request, 'view_sales_history.html', {'customer_orders': orders, 'cashiers': cashiers})

from django.shortcuts import render
from .models import CustomerOrder

def delivery_management(request):
    orders = CustomerOrder.objects.filter(delivery_type='delivery')
    return render(request, 'deliverycustomer.html', {'orders': orders})


from django.http import JsonResponse
from webapp.models import CustomerOrder, Employee, UserLog
import json

def reset_delivery_status(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            order_id = data.get("order_id")
            original_status = data.get("original_status")

            if not order_id or not original_status:
                return JsonResponse({"success": False, "message": "Missing data."})

            # Update the order
            order = CustomerOrder.objects.get(order_id=order_id)
            order.delivery_status = original_status
            order.save()

            # Log the action
            employee_id = request.session.get('employee_id')
            if employee_id:
                try:
                    employee = Employee.objects.get(EmployeeID=employee_id)
                    UserLog.objects.create(
                        employee=employee,
                        action_type=f"Reset delivery status of Order #{order_id} to '{original_status}'"
                    )
                except Employee.DoesNotExist:
                    return JsonResponse({"success": False, "message": "Logged-in employee not found."})
            else:
                return JsonResponse({"success": False, "message": "User not authenticated."})

            return JsonResponse({"success": True})

        except CustomerOrder.DoesNotExist:
            return JsonResponse({"success": False, "message": "Order not found."})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})

    return JsonResponse({"success": False, "message": "Invalid request method."})


from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from webapp.models import CustomerOrder, UserLog, Employee
import json

@csrf_exempt
def update_delivery_status(request):
    if request.method == "POST":
        data = json.loads(request.body)
        order_id = data.get("order_id")
        new_status = data.get("status")

        if not order_id or not new_status:
            return JsonResponse({"success": False, "message": "Missing order_id or status."})

        try:
            order = CustomerOrder.objects.get(order_id=order_id)
            order.delivery_status = new_status
            order.save()

            # Record in user logs
            employee_id = request.session.get('employee_id')
            if employee_id:
                try:
                    employee = Employee.objects.get(EmployeeID=employee_id)
                    UserLog.objects.create(
                        employee=employee,
                        action_type=f"Updated delivery status of Order #{order_id} to '{new_status}'"
                    )
                except Employee.DoesNotExist:
                    return JsonResponse({"success": False, "message": "Logged-in employee not found."})
            else:
                return JsonResponse({"success": False, "message": "User not authenticated."})

            return JsonResponse({"success": True})

        except CustomerOrder.DoesNotExist:
            return JsonResponse({"success": False, "message": "Order not found."})

    return JsonResponse({"success": False, "message": "Invalid request method."})


# views.py
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from webapp.models import Users, Supplier, UserLog  # Import UserLog model

def supplier_order(request):
    if request.method == 'POST':
        try:
            supplier_name = request.POST.get('supplier_name')
            supplier_contact = request.POST.get('supplier_contact')
            employee_id = request.POST.get('employee_id')
            rice_per_kilo = request.POST.get('rice_per_kilo')
            kilo_of_rice = request.POST.get('kilo_of_rice')
            paid_amount = request.POST.get('paid_amount')
            payment_method = request.POST.get('payment_method')
            delivery_method = request.POST.get('delivery_method', 'Delivery')

            total_cost = float(rice_per_kilo) * int(kilo_of_rice)
            change_amount = float(paid_amount) - total_cost


            # Get the user object (cashier or whoever is logged in)

            employee = None
            if employee_id:
                try:
                    employee = Employee.objects.get(EmployeeID=employee_id)
                except Employee.DoesNotExist:
                    employee = None

            supplier_order = Supplier.objects.create(
                supplier_name=supplier_name,
                supplier_contact=supplier_contact,
                employee=employee,
                rice_per_kilo=rice_per_kilo,
                kilo_of_rice=kilo_of_rice,
                total_cost=total_cost,
                paid_amount=paid_amount,
                change_amount=change_amount,
                approval_status='Pending',
                delivery_method=delivery_method,
                payment_method=payment_method,
                purchase_date=timezone.now()
            )

            # Create user log entry

            log_message = (f"Created supplier order ID {supplier_order.id} for supplier '{supplier_name}', "
                           f"total cost ₱{total_cost:.2f}, payment method: {payment_method}, delivery: {delivery_method}.")
            UserLog.objects.create(
                employee=employee,
                action_type="Created supplier order",
                details=log_message,
                timestamp=timezone.now()
            )

            messages.success(request, "Supplier order submitted successfully.")
            return redirect('supplier_order')

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    employees = Users.objects.filter(Role='employee')
    return render(request, 'supplierorder.html', {'employees': employees})


from webapp.models import Employee, Supplier, UserLog

def process_supplier(request):
    if request.method == 'POST':
        try:
            supplier_name = request.POST.get('supplier_name')
            supplier_contact = request.POST.get('supplier_contact')
            employee_id = request.POST.get('employee_id')
            rice_per_kilo = request.POST.get('rice_per_kilo')
            kilo_of_rice = request.POST.get('kilo_of_rice')
            paid_amount = request.POST.get('paid_amount')
            payment_method = request.POST.get('payment_method')
            delivery_method = request.POST.get('delivery_method', 'Delivery')

            total_cost = float(rice_per_kilo) * int(kilo_of_rice)
            change_amount = float(paid_amount) - total_cost


            # Get the user object (cashier or whoever is logged in)

            employee = Employee.objects.get(EmployeeID=employee_id)

            supplier_order = Supplier.objects.create(
                supplier_name=supplier_name,
                supplier_contact=supplier_contact,
                employee=employee,
                rice_per_kilo=rice_per_kilo,
                kilo_of_rice=kilo_of_rice,
                total_cost=total_cost,
                paid_amount=paid_amount,
                change_amount=change_amount,
                approval_status='Pending',
                delivery_method=delivery_method,
                payment_method=payment_method,
                purchase_date=timezone.now()
            )


            # Record to user_logs (optional: you may want to use user or keep employee for logs)
            UserLog.objects.create(
                employee=employee,
                action_type=f"Created supplier order for '{supplier_name}' worth ₱{total_cost:.2f}."
            )

            messages.success(request, "Supplier order submitted successfully.")
            return redirect('supplier_order')

        except Employee.DoesNotExist:
            return JsonResponse({
                "status": "error",
                "message": "No matching Employee record. Please ensure this Employee exists."
            })

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    employees = Employee.objects.all()
    return render(request, 'supplierorder.html', {'employees': employees})

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

@require_POST
def update_supplier_status(request, supplier_id):
    try:
        data = json.loads(request.body)
        new_status = data.get('status')

        if new_status not in ['Approved', 'Declined']:
            return JsonResponse({'success': False, 'error': 'Invalid status'})

        supplier = get_object_or_404(Supplier, pk=supplier_id)
        supplier.approval_status = new_status
        supplier.save()

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
        
def delete_supplier(request, supplier_id):
    if request.method == "POST":
        supplier = Supplier.objects.get(pk=supplier_id)
        supplier.delete()
        return JsonResponse({'status': 'success'})


from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings
import subprocess
import tempfile
import os

@require_POST
@csrf_protect
def backup_database(request):
    # MySQL settings
    db_name = "dragonricemill"
    db_user = "root"
    db_password = "password"  # Store this in environment or Django settings for security

    try:
        # Use a secure temporary file to store the backup
        with tempfile.NamedTemporaryFile(delete=False, suffix=".sql") as temp_file:
            backup_path = temp_file.name

        # Build mysqldump command
        command = [
            "mysqldump",
            f"-u{db_user}",
            f"-p{db_password}",
            db_name,
        ]

        # Run the command and write output to the backup path
        with open(backup_path, "w") as f:
            result = subprocess.run(command, stdout=f, stderr=subprocess.PIPE, text=True)

        # Check for errors
        if result.returncode != 0:
            messages.error(request, "Database backup failed.")
            os.remove(backup_path)
            return redirect('logs')

        # Serve the backup file as a downloadable response
        with open(backup_path, "rb") as f:
            response = HttpResponse(f.read(), content_type='application/sql')
            response['Content-Disposition'] = 'attachment; filename=dragonricemill_backup.sql'

        # Clean up temp file
        os.remove(backup_path)

        return response

    except Exception as e:
        messages.error(request, f"An error occurred during backup: {str(e)}")
        return redirect('logs')


from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings
import subprocess
import tempfile
import os

@require_POST
@csrf_protect
def restore_database(request):
    uploaded_file = request.FILES.get("backup_file")

    if not uploaded_file:
        messages.error(request, "No file uploaded.")
        return redirect('logs')

    if not uploaded_file.name.endswith(".sql"):
        messages.error(request, "Invalid file format. Please upload a .sql file.")
        return redirect('logs')

    try:
        # Save uploaded SQL to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".sql") as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        # DB credentials
        db_name = "dragonricemill"
        db_user = "root"
        db_password = "password"  # You can store this in Django settings for safety

        # Restore database using subprocess
        command = [
            "mysql",
            f"-u{db_user}",
            f"-p{db_password}",
            db_name
        ]

        with open(temp_file_path, "rb") as sql_file:
            result = subprocess.run(command, stdin=sql_file, stderr=subprocess.PIPE, text=True)

        os.remove(temp_file_path)

        if result.returncode == 0:
            messages.success(request, "Database restored successfully.")
        else:
            messages.error(request, f"Restore failed: {result.stderr}")

    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")

    return redirect('logs')


from django.contrib.auth.hashers import make_password
from django.db import IntegrityError
from django.shortcuts import render
from .models import UserName, UserAddress, Users

def Process_signup(request):
    if request.method == 'POST':
        # Get fields similar to adduser
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        first_name = request.POST.get('first_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        suffix = request.POST.get('suffix', '').strip()
        role = 'employee'  # Default role for signup

        # Validation (same as adduser)
        if not (username and password and first_name and last_name and role):
            return render(request, 'signup.html', {'error': 'Please fill in all required fields.'})

        # Create the employee (inactive by default)
        from .models import Employee
        try:
            new_employee = Employee(
                Username=username,
                Password=password,
                FirstName=first_name,
                MiddleName=middle_name,
                LastName=last_name,
                Suffix=suffix,
                Role=role,
                Account_Status='inactive'
            )
            new_employee.save()
            return render(request, 'signup.html', {
                'success': 'Signup successful! Your account is pending activation by an admin.'
            })
        except Exception as e:
            return render(request, 'signup.html', {
                'error': f'Error creating user: {str(e)}'
            })

    return render(request, 'signup.html')


# --- Customer Account Overview View ---
from .models import CustomerOrder, Users
from django.shortcuts import render, redirect

def user_account_view(request):
    """
    Show customer account overview: profile info and their orders.
    """
    user_id = request.session.get('user_id')
    user_role = request.session.get('user_role')
    if not user_id or not user_role:
        return redirect('login')

    if user_role == 'admin':
        # Just get all customers (all users), no role filtering since Role field doesn't exist
        customers = Users.objects.all().order_by('name__last_name', 'name__first_name')

        customer_id = request.GET.get('customer_id')
        selected_customer = None
        orders = None
        if customer_id:
            selected_customer = Users.objects.filter(UserID=customer_id).select_related('name', 'address').first()
            orders = CustomerOrder.objects.filter(customer_id=customer_id).order_by('-created_at')
        return render(request, 'user_account.html', {
            'customers': customers,
            'selected_customer': selected_customer,
            'orders': orders,
            'is_admin': True,
        })

    if user_role == 'user':
        user = Users.objects.filter(UserID=user_id).first()
        orders = CustomerOrder.objects.filter(customer_id=user_id).order_by('-created_at')
        return render(request, 'user_account.html', {
            'user': user,
            'orders': orders,
            'is_admin': False,
        })

    return redirect('dashboard')
