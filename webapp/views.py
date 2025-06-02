from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from .models import UserLog, Rice, Users, CustomerOrder, UserName, UserAddress
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from .models import UserLog, Rice, Stock

from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from .models import CustomerOrder
from django.shortcuts import render, get_object_or_404
from .models import CustomerOrder  # or whatever your order model is named
from django.views.decorators.csrf import csrf_exempt

from decimal import Decimal, InvalidOperation
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from webapp.models import CustomerOrder
from decimal import Decimal, InvalidOperation
from django.shortcuts import render
from django.http import HttpResponse
from webapp.models import CustomerOrder
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
import textwrap

from decimal import Decimal, InvalidOperation
from django.http import HttpResponse
from django.shortcuts import render
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from .models import CustomerOrder

from django.shortcuts import render, redirect
from .models import Users, CustomerOrder, CustomerLedger
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect


from django.shortcuts import render
from django.db.models import Sum, F
from datetime import datetime
from .models import Stock

from django.shortcuts import render
from .models import Stock

from django.shortcuts import render
from .models import Stock

def stock_movement_report(request):
    stock_data = Stock.objects.select_related('rice_type').all()
    return render(request, 'view_sales_report.html', {'stock_movement_data': stock_data})



def customer_ledger_create(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        order_id = request.POST.get('order') or None
        transaction_type = request.POST.get('transaction_type')
        reference = request.POST.get('reference')
        amount = request.POST.get('amount')
        remarks = request.POST.get('remarks')

        try:
            customer = Users.objects.get(UserID=customer_id)
        except Users.DoesNotExist:
            return render(request, 'ledger_entry.html', {
                'error': 'Selected customer does not exist.',
                'customers': Users.objects.all()
            })

        order = None
        if order_id:
            try:
                order = CustomerOrder.objects.get(order_id=order_id, customer=customer)
            except CustomerOrder.DoesNotExist:
                return render(request, 'ledger_entry.html', {
                    'error': 'Selected order does not exist for this customer.',
                    'customers': Users.objects.all()
                })

        # Create ledger entry
        ledger = CustomerLedger(
            customer=customer,
            order=order,
            transaction_type=transaction_type,
            reference=reference,
            amount=amount,
            remarks=remarks,
        )
        ledger.save()

        return render(request, 'ledger.html', {
            'message': 'Customer ledger entry created successfully.',
            'customers': Users.objects.all()
        })

    # GET request, render form
    customers = Users.objects.all()
    return render(request, 'ledger.html', {'customers': customers})


from django.http import JsonResponse
from .models import CustomerOrder, Users

def orders_for_customer(request, customer_id):
    try:
        print(f"Fetching orders for customer_id={customer_id}")
        orders = CustomerOrder.objects.filter(customer__UserID=customer_id).order_by('-created_at').values('order_id', 'created_at')
        orders_list = list(orders)
        for o in orders_list:
            if o['created_at']:
                o['created_at'] = o['created_at'].strftime('%Y-%m-%d')
            else:
                o['created_at'] = ''
        print(f"Found orders: {orders_list}")
        return JsonResponse(orders_list, safe=False)
    except Exception as e:
        print(f"Error in orders_for_customer view: {e}")
        return JsonResponse({'error': str(e)}, status=400)



def money_fmt(val):
    """Format Decimal as pesos with commas and 2 decimals."""
    return f"₱{format(val, ',.2f')}"

from decimal import Decimal, InvalidOperation
from django.http import HttpResponse
from django.shortcuts import render
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from .models import CustomerOrder

def safe_decimal(value, default=Decimal('0.00')):
    """Safely convert value to Decimal, return default if invalid."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default

def money_fmt(amount):
    """Format Decimal as currency string. Adjust as needed."""
    return f"₱{amount:,.2f}"

from decimal import Decimal, InvalidOperation
from django.shortcuts import render
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from .models import CustomerOrder


# --- Utility Functions ---
def safe_decimal(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")

def money_fmt(value):
    return f"₱{safe_decimal(value):,.2f}"

from decimal import Decimal, InvalidOperation
from django.shortcuts import render
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from .models import CustomerOrder

def invoice_view(request): 
    orders = CustomerOrder.objects.all().order_by('-created_at')
    selected_order = None
    order_id = request.POST.get('order_id') or request.GET.get('order_id')

    if order_id:
        try:
            selected_order = CustomerOrder.objects.get(order_id=order_id)

            # Calculate safe values
            selected_order.safe_cost_per_sack = safe_decimal(selected_order.cost_per_sack)
            selected_order.safe_quantity = safe_decimal(selected_order.quantity)
            selected_order.safe_discount = safe_decimal(getattr(selected_order, 'discount', 0))

            discount_ratio = selected_order.safe_discount / Decimal("100")
            discounted_total = selected_order.safe_cost_per_sack * selected_order.safe_quantity * (1 - discount_ratio)
            selected_order.safe_total = discounted_total.quantize(Decimal("0.01"))

        except CustomerOrder.DoesNotExist:
            selected_order = None

    # --- Handle PDF Export ---
    if request.method == "POST" and "export_pdf" in request.POST and selected_order:
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=receipt_{order_id}.pdf'

        PAGE_WIDTH = 100 * mm
        PAGE_HEIGHT = 200 * mm
        LEFT_MARGIN = 15
        LINE_HEIGHT = 14

        p = canvas.Canvas(response, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
        p.setFont("Helvetica", 11)

        y = PAGE_HEIGHT - 20

        def line(text='', gap=LINE_HEIGHT, bold=False, align_right=False, value=None):
            nonlocal y
            p.setFont("Helvetica-Bold", 11) if bold else p.setFont("Helvetica", 11)
            if align_right and value is not None:
                p.drawString(LEFT_MARGIN, y, text)
                p.drawRightString(PAGE_WIDTH - LEFT_MARGIN, y, str(value))
            else:
                p.drawString(LEFT_MARGIN, y, text)
            y -= gap

        line("Dragon Ricemill Receipt", bold=True)
        line()
        line(f"Invoice Number: INV-{order_id}", bold=True)
        line(f"Customer: {getattr(selected_order.customer, 'name', 'Unknown')}")
        line(f"Address: {getattr(selected_order.customer, 'address', 'Unknown')}")
        line()
        line(f"Rice Type: {selected_order.rice_type.rice_type}")
        line(f"Quantity: {selected_order.quantity} sack(s)")
        line(f"Cost Per Sack: {money_fmt(selected_order.safe_cost_per_sack)}")
        line(f"Discount: {selected_order.discount}%")
        line(f"Total Cost: {money_fmt(selected_order.safe_total)}")
        line(f"Payment Method: {selected_order.payment_method}")
        line(f"Amount Paid: {money_fmt(selected_order.amount_paid)}")
        line(f"Change: {money_fmt(selected_order.amount_change)}")
        line()
        line("Thank you for your purchase!", bold=True)

        p.showPage()
        p.save()
        return response

    # --- Render Invoice Print Preview ---
    if order_id and selected_order and request.method == "GET":
        context = {
            'order': selected_order,
            'invoice_number': f'INV-{order_id}',
            'formatted_discount': f"{selected_order.discount}%",
            'money_fmt': money_fmt,
        }
        return render(request, 'invoice_print.html', context)

    # --- Render Invoice Selector Page ---
    context = {
        'orders': orders,
        'order': selected_order,
        'invoice_number': f'INV-{order_id or "N/A"}',
    }
    return render(request, 'invoice.html', context)


@require_POST
def undo_update(request, log_id):
    # Check if it's an AJAX request
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    try:
        # Get the log entry
        log = get_object_or_404(UserLog, id=log_id)

        # Only proceed if the log is an "add stock" entry and not yet undone
        if not log.action_type.startswith('Added') or 'sacks to' not in log.action_type:
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': 'Undo not allowed for this action.'}, status=400)
            messages.error(request, 'Undo not allowed for this action.')
            return redirect('addstock')

        if '(Undone)' in log.action_type:
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': 'This action has already been undone.'}, status=400)
            messages.error(request, 'This action has already been undone.')
            return redirect('addstock')

        try:
            parts = log.action_type.split()
            quantity = int(parts[1])
            rice_type = ' '.join(parts[4:]).strip()
            # Remove packaging info from rice type if present
            rice_type = rice_type.split('(')[0].strip()
        except Exception:
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': 'Malformed log entry.'}, status=400)
            messages.error(request, 'Malformed log entry.')
            return redirect('addstock')

        # Try to find the rice
        rice = Rice.objects.filter(rice_type__iexact=rice_type).first()
        if not rice:
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': f'Rice type not found: {rice_type}'}, status=404)
            messages.error(request, f'Rice type not found: {rice_type}')
            return redirect('addstock')

        # Get stock (assumes default packaging is 50kg)
        stock = Stock.objects.filter(rice_type=rice).first()
        if not stock:
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': 'Stock record not found.'}, status=404)
            messages.error(request, 'Stock record not found.')
            return redirect('addstock')

        # Perform undo: subtract stock_in
        stock.stock_in = max(0, stock.stock_in - quantity)
        stock.current_stock = max(0, stock.stock_in - stock.stock_out)
        stock.save()

        # Append "(Undone)" to log.action_type
        log.action_type = f"{log.action_type} (Undone)"
        log.save()

        if is_ajax:
            return JsonResponse({'status': 'success', 'message': 'Undo successful.'})
        messages.success(request, 'Stock update has been successfully undone.')
        return redirect('addstock')

    except Exception as e:
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('addstock')


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
from django.db import transaction
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


from datetime import date
from django.db.models import Sum
from django.utils.timezone import now
from .models import CustomerOrder, Stock, Supplier, Announcement, Employee, Users

# Assuming you have PH_TZ defined somewhere in your timezone settings
from pytz import timezone
PH_TZ = timezone('Asia/Manila')

def dashboard_view(request):
    is_admin = False
    role = None
    employee_id = None

    # Use session to determine user type and get info
    user_id = request.session.get('user_id')
    user_role = request.session.get('user_role', '').lower()
    if user_id and user_role:
        if user_role in ['admin', 'cashier', 'employee']:
            try:
                custom_user = Employee.objects.get(EmployeeID=user_id)
                employee_id = custom_user.EmployeeID
                role = custom_user.Role.strip().lower()
                is_admin = (role == 'admin')
            except Employee.DoesNotExist:
                pass
        else:
            try:
                custom_user = Users.objects.get(UserID=user_id)
                role = user_role
                is_admin = (role == 'admin')
            except Users.DoesNotExist:
                pass

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

    # Calculate best-selling and lowest-selling rice types
    sales_aggregation = CustomerOrder.objects.filter(approval_status='Approved') \
        .values('rice_type__rice_type') \
        .annotate(total_quantity=Sum('quantity')) \
        .order_by('-total_quantity')

    best_selling = sales_aggregation.first() if sales_aggregation else None
    low_selling = sales_aggregation.last() if sales_aggregation else None

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
        'best_selling': best_selling,
        'low_selling': low_selling,
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
from webapp.models import UserName, UserAddress, Users  # Adjust if needed

@require_http_methods(["GET", "POST"])
def add_customer(request):
    if request.method == 'GET':
        return render(request, 'add_customer.html')
        
    elif request.method == 'POST':
        try:
            # Extract form data
            first_name = request.POST.get('first_name')
            middle_name = request.POST.get('middle_name', '')
            last_name = request.POST.get('last_name')
            suffix = request.POST.get('suffix', '')
            customer_mobile_number = request.POST.get('customer_mobile_number')
            house_unit_number = request.POST.get('house_unit_number')
            building_name = request.POST.get('building_name', '')
            street_name = request.POST.get('street_name', '')
            barangay = request.POST.get('barangay')
            city_municipality = request.POST.get('city_municipality')
            province = request.POST.get('province')
            zip_code = request.POST.get('zip_code')

            # Validate required fields
            if not all([first_name, last_name, customer_mobile_number, house_unit_number, 
                       street_name, barangay, city_municipality, province, zip_code]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'add_customer.html')

            # Create UserName record
            user_name = UserName.objects.create(
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                suffix=suffix
            )

            # Create UserAddress record
            user_address = UserAddress.objects.create(
                house_unit_number=house_unit_number,
                building_name=building_name,
                street_name=street_name,
                barangay=barangay,
                city_municipality=city_municipality,
                province=province,
                zip_code=zip_code
            )

            # Create Users record with the related models
            user = Users.objects.create(
                name=user_name,
                address=user_address,
                Customer_Mobile_Number=customer_mobile_number
            )

            messages.success(request, 'Customer added successfully!')
            return render(request, 'add_customer.html')

        except Exception as e:
            messages.error(request, f'Error adding customer: {str(e)}')
            return render(request, 'add_customer.html')



from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.shortcuts import render, redirect
from .models import Rice, Stock, CustomerOrder, Users, UserName, UserAddress, Employee

def new_sale_view(request):
    if request.method == 'POST':
        try:
            # Get form data
            rice_type_id = request.POST.get('rice_type_id')
            quantity = request.POST.get('quantity')
            cost_per_sack = request.POST.get('cost_per_sack')
            total_cost = request.POST.get('total_cost')
            amount_paid = request.POST.get('amount_paid')
            amount_change = request.POST.get('amount_change')

            # Create UserName instance
            user_name = UserName.objects.create(
                first_name=request.POST.get('first_name', ''),
                middle_name=request.POST.get('middle_name', ''),
                last_name=request.POST.get('last_name', ''),
                suffix=request.POST.get('suffix', '')
            )

            # Create UserAddress instance
            user_address = UserAddress.objects.create(
                house_unit_number=request.POST.get('house_unit_number', ''),
                building_name=request.POST.get('building_name', ''),
                street_name=request.POST.get('street_name', ''),
                barangay=request.POST.get('barangay', ''),
                city_municipality=request.POST.get('city_municipality', ''),
                province=request.POST.get('province', ''),
                zip_code=request.POST.get('zip_code', '')
            )

            # Get or create Users instance
            customer, _ = Users.objects.get_or_create(
                name=user_name,
                defaults={
                    'address': user_address,
                    'Customer_Mobile_Number': request.POST.get('customer_contact', ''),
                }
            )

            # Get Rice object
            try:
                rice = Rice.objects.get(riceID=rice_type_id)
            except Rice.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Selected rice type does not exist.'})

            # Get employee
            employee = None
            employee_id = request.POST.get('employee_id')
            if employee_id:
                employee = Employee.objects.filter(EmployeeID=employee_id).first()

            # Parse numeric fields
            def parse_decimal(value, field_name):
                try:
                    return Decimal(str(value))
                except (InvalidOperation, TypeError, ValueError):
                    raise ValueError(f"Invalid {field_name}.")

            try:
                quantity = int(request.POST.get('quantity', 0))
                if quantity <= 0:
                    return JsonResponse({'status': 'error', 'message': 'Quantity must be greater than 0.'})

                cost_per_sack = parse_decimal(request.POST.get('cost_per_sack', '0'), 'cost per sack')
                total_cost = parse_decimal(request.POST.get('total_cost', '0'), 'total cost')
                amount_paid = parse_decimal(request.POST.get('amount_paid', '0'), 'amount paid')
                amount_change = parse_decimal(request.POST.get('amount_change', '0'), 'amount change')
            except ValueError as e:
                return JsonResponse({'status': 'error', 'message': str(e)})

            # Create the CustomerOrder
            CustomerOrder.objects.create(
                customer=customer,
                rice_type=rice,
                quantity=quantity,
                cost_per_sack=cost_per_sack,
                total_cost=total_cost,
                payment_method=request.POST.get('payment_method', '').lower(),
                amount_paid=amount_paid,
                amount_change=amount_change,
                delivery_type=request.POST.get('delivery_type', 'delivery').lower(),
                delivery_status='pending',
                approval_status='pending',  # Always set to pending initially
                employee=employee,
                is_active=True
            )

            return redirect('view_sales_history')

        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred. Please try again.'})

    # GET method – show form with related stock and rice data
    stock_data = Stock.objects.select_related('rice_type').all()
    cashier_admin_users = Employee.objects.filter(Role__in=['Cashier', 'Admin'], Account_Status='active')
    customer_users = Users.objects.filter(name__isnull=False)

    return render(request, 'sales_transaction.html', {
        'stock_data': stock_data,
        'cashier_admin_users': cashier_admin_users,
        'customer_users': customer_users,
    })



def view_sales_report(request):
    return render(request, 'view_sales_report.html', {})

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


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from webapp.models import Stock
import json

@csrf_exempt
def update_stock(request, stockID):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            price = data.get('price_per_sack')
            desc = data.get('description')

            if price is None:
                return JsonResponse({'status': 'error', 'message': 'Price is required'}, status=400)

            try:
                price = Decimal(price)
                if price < 0:
                    return JsonResponse({'status': 'error', 'message': 'Price cannot be negative'}, status=400)
            except (InvalidOperation, TypeError, ValueError):
                return JsonResponse({'status': 'error', 'message': 'Invalid price format'}, status=400)

            stock = get_object_or_404(Stock, stockID=stockID)
            stock.price_per_sack = price
            stock.save()

            if desc is not None:
                rice = stock.rice_type
                rice.description = desc
                rice.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Stock updated successfully!',
                'data': {
                    'price': float(stock.price_per_sack),
                    'description': stock.rice_type.description
                }
            })
        except Stock.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Stock not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


def removestock(request):
    return render(request, 'removestock.html')

from django.shortcuts import render
from .models import Stock

def viewstocklevel(request):
    stock_data = Stock.objects.select_related('rice_type').all()
    rice_types = Rice.objects.values_list('rice_type', flat=True).distinct()
    packaging_types = Stock.objects.values_list('packaging', flat=True).distinct()

    # Calculate stock counts
    total_stock_count = stock_data.count()
    low_stock_count = stock_data.filter(current_stock__gt=0, current_stock__lte=100).count()
    out_of_stock_count = stock_data.filter(current_stock=0).count()
    in_stock_count = stock_data.filter(current_stock__gt=100).count()

    context = {
        'stock_data': stock_data,
        'rice_types': rice_types,
        'packaging_types': packaging_types,
        'total_stock_count': total_stock_count,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'in_stock_count': in_stock_count,
    }
    return render(request, 'viewstocklevel.html', context)

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
    # Get search and filter parameters
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '').lower()
    status_filter = request.GET.get('status', '').lower()
    
    # Get all users and apply filters
    users = Employee.objects.all().order_by('EmployeeID')
    
    if search_query:
        users = users.filter(
            Q(Username__icontains=search_query) |
            Q(FirstName__icontains=search_query) |
            Q(LastName__icontains=search_query)
        )
    
    if role_filter:
        users = users.filter(Role__iexact=role_filter)
    
    if status_filter:
        users = users.filter(Account_Status__iexact=status_filter)

    # Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(users, 10)  # Show 10 users per page
    users_page = paginator.get_page(page_number)
    
    # Get deleted users with pagination
    deleted_users = Employee.objects.filter(Account_Status__iexact='deleted').order_by('EmployeeID')
    deleted_paginator = Paginator(deleted_users, 10)
    deleted_page = deleted_paginator.get_page(request.GET.get('deleted_page', 1))

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
    else:
        selected_user = None

    # Define all possible roles and statuses
    all_roles = ['Admin', 'Employee', 'Cashier']
    all_statuses = ['Active', 'Inactive']

    context = {
        'users': users_page,
        'deleted_users': deleted_page,
        'selected_user': selected_user,
        'all_roles': all_roles,
        'all_statuses': all_statuses,
        'current_role': role_filter.capitalize() if role_filter else '',
        'current_status': status_filter.capitalize() if status_filter else '',
    }
    
    return render(request, 'edituser.html', context)


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
from .models import Rice, Stock, UserLog, Employee
from django.utils import timezone
from django.contrib import messages

def addstock(request):
    if request.method == "POST":
        rice_type_id = request.POST.get("riceType")
        quantity = request.POST.get("quantity")
        packaging = request.POST.get("packaging", "50kg")  # default to 50kg
        employee_id = request.session.get('employee_id')

        if not rice_type_id or not quantity:
            messages.error(request, 'All fields are required.')
            return render(request, 'addstock.html', {
                'rice_data': Rice.objects.all(),
                'stock_data': Stock.objects.select_related('rice_type').all(),
                'update_logs': []
            })

        try:
            rice = Rice.objects.get(riceID=rice_type_id)
        except Rice.DoesNotExist:
            messages.error(request, 'Selected rice type does not exist.')
            return render(request, 'addstock.html', {
                'rice_data': Rice.objects.all(),
                'stock_data': Stock.objects.select_related('rice_type').all(),
                'update_logs': []
            })

        try:
            quantity_int = int(quantity)
            if quantity_int <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, 'Quantity must be a positive integer.')
            return render(request, 'addstock.html', {
                'rice_data': Rice.objects.all(),
                'stock_data': Stock.objects.select_related('rice_type').all(),
                'update_logs': []
            })

        # Get or create stock record
        stock_obj, created = Stock.objects.get_or_create(
            rice_type=rice,
            packaging=packaging,
            defaults={
                'stock_in': 0,
                'stock_out': 0,
                'price_per_sack': 0,
                'current_stock': 0
            }
        )

        # Update stock_in and current_stock
        stock_obj.stock_in += quantity_int
        stock_obj.current_stock = stock_obj.stock_in - stock_obj.stock_out
        stock_obj.save()

        # Record log if employee is logged in
        if employee_id:
            try:
                employee_obj = Employee.objects.get(pk=employee_id)
                action = f"Added {quantity_int} sacks to {rice.rice_type} ({packaging})"
                UserLog.objects.create(
                    employee=employee_obj,
                    action_type=action,
                    timestamp=timezone.now()
                )
                messages.success(request, f'Successfully added {quantity_int} sacks of {rice.rice_type}.')
            except Employee.DoesNotExist:
                messages.warning(request, 'Stock added but employee log not recorded.')

        return redirect('addstock')

    # Get logs for display
    logs = UserLog.objects.select_related('employee').filter(
        action_type__startswith='Added',
        action_type__contains='sacks to'
    ).order_by('-timestamp')[:20]
    
    update_logs = []
    for log in logs:
        try:
            parts = log.action_type.split()
            quantity = int(parts[1])
            rice_type = ' '.join(parts[4:])  # e.g., "Dinorado (50kg)"
        except (IndexError, ValueError):
            continue  # Skip malformed log entries
            
        undone = '(Undone)' in log.action_type
        update_logs.append({
            'id': log.id,
            'action': 'add_stock',
            'quantity_added': quantity,
            'rice_type': rice_type,
            'timestamp': log.timestamp,
            'undone': undone,
            'user_full_name': f"{log.employee.FirstName} {log.employee.LastName}" if log.employee else '',
            'user_role': log.employee.Role if log.employee else ''
        })

    return render(request, 'addstock.html', {
        'rice_data': Rice.objects.all(),
        'stock_data': Stock.objects.select_related('rice_type').all(),
        'update_logs': update_logs
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

from decimal import Decimal, InvalidOperation
import json
from django.http import JsonResponse
from .models import Rice, Stock

def add_rice(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rice_type = data.get('rice_type')
            price_per_sack = data.get('price_per_sack')  # Optional now
            description = data.get('description', '')    # Optional
            packaging = data.get('packaging', '50kg')    # Default to 50kg

            if not rice_type:
                return JsonResponse({'status': 'error', 'message': 'Rice type is required'})

            # Handle optional price_per_sack, default to 0.00 if missing or empty
            try:
                price = Decimal(price_per_sack) if price_per_sack not in [None, ''] else Decimal('0.00')
                if price < 0:
                    raise InvalidOperation
            except (InvalidOperation, TypeError, ValueError):
                return JsonResponse({'status': 'error', 'message': 'Price per sack must be a non-negative decimal number'})

            # Check for duplicate rice type
            if Rice.objects.filter(rice_type__iexact=rice_type).exists():
                return JsonResponse({'status': 'error', 'message': 'Rice type already exists'})

            # Create new Rice object
            new_rice = Rice.objects.create(
                rice_type=rice_type,
                description=description
            )

            # Create corresponding Stock with price defaulting to 0.00
            stock = Stock.objects.create(
                rice_type=new_rice,
                packaging=packaging,
                price_per_sack=price,
                stock_in=0,
                stock_out=0
            )

            # Prepare response
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
                'message': 'Rice type successfully created',
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

from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.utils.crypto import get_random_string
from .models import CustomerOrder, Stock, Users, Employee

def process_order(request):
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

    stock_id = request.POST.get("stock_id")
    customer_id = request.POST.get("customer_id")
    reference_code = request.POST.get("reference_code")
    delivery_type = request.POST.get("delivery_type", "delivery").lower()
    payment_method = request.POST.get("payment_method", "cash").lower()

    print(f"Processing order - Delivery Type: {delivery_type}, Payment Method: {payment_method}")

    if not stock_id:
        return JsonResponse({'status': 'error', 'message': 'Please select a rice type.'})
    if not customer_id:
        return JsonResponse({'status': 'error', 'message': 'Customer ID is required.'})

    try:
        stock = Stock.objects.select_related('rice_type').get(stockID=stock_id)
    except Stock.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Selected stock does not exist.'})

    try:
        customer = Users.objects.select_related('address').get(UserID=customer_id)
    except Users.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Customer not found.'})

    employee = None
    employee_id = request.POST.get("employee_id")
    if employee_id:
        try:
            employee = Employee.objects.get(EmployeeID=employee_id)
        except Employee.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Employee not found.'})

    try:
        quantity = int(request.POST.get("quantity", 0))
        cost_per_sack = Decimal(str(request.POST.get("cost_per_sack", '0')))
        discount = Decimal(str(request.POST.get("discount", '0')))
        amount_paid = Decimal(str(request.POST.get("amount_paid", '0')))
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Invalid numeric input.'})

    total_cost = (cost_per_sack * quantity) - discount
    total_cost = max(total_cost, Decimal('0.00'))
    amount_change = max(amount_paid - total_cost, Decimal('0.00'))

    print(f"Order details - Total Cost: {total_cost}, Amount Paid: {amount_paid}")

    try:
        order = CustomerOrder.objects.create(
            customer=customer,
            rice_type=stock.rice_type,
            quantity=quantity,
            cost_per_sack=cost_per_sack,
            discount=discount,
            total_cost=total_cost,
            payment_method=payment_method,
            amount_paid=amount_paid,
            amount_change=amount_change,
            delivery_type=delivery_type,
            delivery_status='pending',
            approval_status='pending',  # Always set to pending initially
            employee=employee,
            is_active=True
        )
        print(f"Order created successfully - ID: {order.order_id}, Active: {order.is_active}")
        return JsonResponse({'status': 'success', 'message': 'Order created successfully.'})
    except Exception as e:
        print(f"Error creating order: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Order creation failed: {str(e)}'})



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
from django.views.decorators.csrf import csrf_protect


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
        # If delivery+cash, set delivery_status to 'delivered' so it appears in allorder_history
        if order.delivery_type.lower() == 'delivery' and order.payment_method.lower() == 'cash':
            order.delivery_status = 'delivered'
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


from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.db.models import Q
from urllib.parse import urlencode

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

    supplier_orders = Supplier.objects.filter(approval_status__iexact='approved').order_by('-purchase_date')

    orders = orders.order_by('-created_at')

    # PAGINATION
    paginator = Paginator(orders, 10)  # Show 10 orders per page
    page_number = request.GET.get('page', 1)

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Build querystring for all GET params except 'page'
    querydict = request.GET.copy()
    if 'page' in querydict:
        querydict.pop('page')
    querystring = querydict.urlencode()

    context = {
        'page_obj': page_obj,
        'cashiers': cashiers,
        'supplier_orders': supplier_orders,
        'querystring': querystring,
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
                   (e.FirstName || ' ' || COALESCE(e.MiddleName, '') || ' ' || e.LastName || ' ' || COALESCE(e.Suffix, '')) AS employee_name,
                   e.Role
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
            'role': log[4] or 'N/A',
        })

    # Filter BEFORE pagination
    if filter_date:
        log_entries = [log for log in log_entries if log['date'] == filter_date]
    if filter_time:
        log_entries = [log for log in log_entries if log['time'] == filter_time]
    if filter_action:
        log_entries = [log for log in log_entries if filter_action in log['details'].lower() or filter_action in log['employee_name'].lower() or filter_action in log['role'].lower()]

    paginator = Paginator(log_entries, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'logs.html', {
        'logs': page_obj,
        'page_obj': page_obj,
    })




from django.db.models import Sum, F
from datetime import datetime
from .models import CustomerOrder, Users, Rice

from django.shortcuts import render
from django.db.models import Sum, F
from .models import CustomerOrder  # Make sure your model is imported

from django.db.models import Sum, F, Q, Value, CharField
from django.db.models.functions import Concat, Coalesce
from django.shortcuts import render
from datetime import datetime

from django.shortcuts import render
from django.db.models import Q, Sum, F, Value, CharField
from django.db.models.functions import Concat, Coalesce
from datetime import datetime

from .models import CustomerOrder, Stock  # Adjust your import according to your app structure
from django.db.models.functions import TruncDate

from django.db.models import Sum, F, Value, Q, CharField
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, Coalesce, Concat
from django.shortcuts import render
from datetime import datetime
from .models import CustomerOrder, Stock

def view_sales_report(request):
    group_by = request.GET.get('group_by', 'rice_type')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    sales_period = request.GET.get('sales_period', '')

    filter_conditions = Q()
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            filter_conditions &= Q(created_at__gte=start)
        except ValueError:
            pass
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            filter_conditions &= Q(created_at__lte=end)
        except ValueError:
            pass

    # Choose time truncation based on sales_period
    if sales_period == 'daily':
        trunc_func = TruncDate
    elif sales_period == 'weekly':
        trunc_func = TruncWeek
    elif sales_period == 'monthly':
        trunc_func = TruncMonth
    else:
        trunc_func = TruncDate

    # Main report data
    if group_by == 'cashier':
        report_data = CustomerOrder.objects.filter(filter_conditions) \
            .annotate(
                employee_full_name=Concat(
                    'employee__FirstName', Value(' '),
                    Coalesce('employee__MiddleName', Value('')), Value(' '),
                    'employee__LastName', Value(' '),
                    Coalesce('employee__Suffix', Value('')),
                    output_field=CharField()
                ),
                created_date=trunc_func('created_at')
            ) \
            .values('employee_full_name', 'created_date') \
            .annotate(
                total_quantity=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('cost_per_sack'))
            ) \
            .order_by('employee_full_name', 'created_date')
    else:
        report_data = CustomerOrder.objects.filter(filter_conditions) \
            .annotate(created_date=trunc_func('created_at')) \
            .values('rice_type__rice_type', 'created_date') \
            .annotate(
                total_quantity=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('cost_per_sack'))
            ) \
            .order_by('rice_type__rice_type', 'created_date')

    # Best & Low Selling Rice Types
    best_selling = None
    low_selling = None
    rice_sales = CustomerOrder.objects.filter(filter_conditions) \
        .values('rice_type__rice_type') \
        .annotate(total_quantity=Sum('quantity')) \
        .order_by('-total_quantity')

    if rice_sales.exists():
        best_selling = rice_sales.first()
        low_selling = rice_sales.last()

    # Stock Movement Data
    stock_movement_data = Stock.objects.all().order_by('rice_type__rice_type')

    context = {
        'report_data': report_data,
        'group_by': group_by,
        'start_date': start_date,
        'end_date': end_date,
        'sales_period': sales_period,
        'stock_movement_data': stock_movement_data,
        'best_selling': best_selling,
        'low_selling': low_selling,
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


from django.shortcuts import render
from django.http import JsonResponse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.template.loader import render_to_string

from webapp.models import CustomerOrder, Users  # ✅ Import your models

def view_sales_his(request):
    # Get filter parameters
    search = request.GET.get('search', '').strip()
    cashier_id = request.GET.get('cashier', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    page = request.GET.get('page', 1)

    # Start with all orders and select related foreign keys
    orders = CustomerOrder.objects.select_related('employee', 'rice_type', 'customer').all()

    # Filter by cashier
    if cashier_id:
        orders = orders.filter(employee_id=cashier_id)

    # Filter by date range
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)

    # Filter by search query (customer name or order_id)
    if search:
        orders = orders.filter(
            Q(customer_name__icontains=search) |
            Q(order_id__icontains=search)
        )

    # Paginate the filtered orders
    paginator = Paginator(orders, 10)
    try:
        paginated_orders = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        paginated_orders = paginator.page(1)

    # Return partial HTML if AJAX request
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('partials/orders_table.html', {
            'customer_orders': paginated_orders
        }, request=request)
        return JsonResponse({'html': html})

    # Otherwise, render full page
    cashiers = Users.objects.all()
    return render(request, 'view_sales_history.html', {
        'customer_orders': paginated_orders,
        'cashiers': cashiers
    })

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
                JsonResponse({"success": False, "message": "User not authenticated."})

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
        # Personal Info
        first_name = request.POST.get('first_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        suffix = request.POST.get('suffix', '').strip()

        # Credentials
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        # confirm_password = request.POST.get('confirm_password', '')  # No longer used
        # email = request.POST.get('email', '').strip()  # No longer used

        # Address Info
        house_unit_number = request.POST.get('house_unit_number', '').strip()
        building_name = request.POST.get('building_name', '').strip()
        street_name = request.POST.get('street_name', '').strip()
        barangay = request.POST.get('barangay', '').strip()
        city_municipality = request.POST.get('city_municipality', '').strip()
        province = request.POST.get('province', '').strip()
        zip_code = request.POST.get('zip_code', '').strip()


        # Contact Info
        country_code = request.POST.get('country_code', '').strip()
        mobile_number = request.POST.get('mobile_number', '').strip()
        full_mobile_number = f"{country_code}{mobile_number}" if country_code and mobile_number else ''

        # Validation (no confirm_password, no email)
        if not username or not password or not first_name or not last_name:
            return render(request, 'signup.html', {'error': 'All required fields must be filled.'})


        try:
            # Create Name Object
            name_obj = UserName.objects.create(
                first_name=first_name,
                middle_name=middle_name or None,
                last_name=last_name,
                suffix=suffix or None
            )

            # Create Address Object
            address_obj = UserAddress.objects.create(
                house_unit_number=house_unit_number or None,
                building_name=building_name or None,
                street_name=street_name or None,
                barangay=barangay or None,
                city_municipality=city_municipality or None,
                province=province or None,
                zip_code=zip_code or None
            )

            # Create User
            # Create as Employee instead of Users
            Employee.objects.create(
                FirstName=first_name,
                MiddleName=middle_name or None,
                LastName=last_name,
                Suffix=suffix or None,
                Username=username,
                Password=password,  # Not hashed
                Role='',  # Use empty string instead of None
                Account_Status='inactive'
            )

            return render(request, 'signup.html', {
                'success': True
            })

        except IntegrityError:
            return render(request, 'signup.html', {
                'error': 'Username already exists.'
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

    # Get message from session if exists
    message = request.session.pop('user_account_message', None)

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
            'message': message,
        })

    if user_role == 'user':
        user = Users.objects.filter(UserID=user_id).first()
        orders = CustomerOrder.objects.filter(customer_id=user_id).order_by('-created_at')
        return render(request, 'user_account.html', {
            'user': user,
            'orders': orders,
            'is_admin': False,
            'message': message,
        })

    return redirect('dashboard')

from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from .models import Users

@require_http_methods(["GET", "POST"])
def delete_customer(request, user_id):
    customers = Users.objects.all().select_related('name')
    if user_id == 0:
        # Show selection form only
        return render(request, 'delete_customer.html', {'customers': customers})
    customer = get_object_or_404(Users, UserID=user_id)
    if request.method == "POST":
        customer_name = f"{customer.name.first_name} {customer.name.last_name}"
        customer.delete()
        # Store message in session instead of using messages framework
        request.session['user_account_message'] = {
            'type': 'success',
            'text': f'Customer {customer_name} has been successfully deleted.'
        }
        return redirect('user_account')

from decimal import InvalidOperation
from webapp.models import CustomerOrder
from django.shortcuts import render

from django.shortcuts import render
from webapp.models import CustomerOrder

from django.core.paginator import Paginator
from django.shortcuts import render
from .models import CustomerOrder

def allorder_history(request):
    # Get filter parameters
    search = request.GET.get('search', '')
    payment_method = request.GET.get('payment_method', '')
    delivery_type = request.GET.get('delivery_type', '')
    rice_type = request.GET.get('rice_type', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    order_status = request.GET.get('order_status', '')

    # Base queryset
    orders = CustomerOrder.objects.all()

    # Apply filters
    if search:
        orders = orders.filter(
            Q(order_id__icontains=search) |
            Q(customer__name__first_name__icontains=search) |
            Q(customer__name__last_name__icontains=search) |
            Q(rice_type__rice_type__icontains=search)
        )

    if payment_method:
        orders = orders.filter(payment_method=payment_method)

    if delivery_type:
        orders = orders.filter(delivery_type=delivery_type)

    if rice_type:
        orders = orders.filter(rice_type__rice_type__iexact=rice_type)

    if start_date:
        orders = orders.filter(created_at__gte=start_date)

    if end_date:
        orders = orders.filter(created_at__lte=end_date)

    if order_status:
        orders = orders.filter(approval_status=order_status)
    else:
        # If no status filter, show both confirmed and cancelled orders
        orders = orders.filter(Q(approval_status='confirmed') | Q(approval_status='cancelled'))

    # Calculate statistics
    total_orders = orders.count()
    cancelled_count = orders.filter(approval_status='cancelled').count()
    total_revenue = orders.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    total_quantity = orders.aggregate(Sum('quantity'))['quantity__sum'] or 0

    # Get unique rice types for filter
    rice_types = Rice.objects.all()

    # Pagination
    paginator = Paginator(orders.order_by('-created_at'), 10)
    page = request.GET.get('page')
    try:
        page_obj = paginator.get_page(page)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    context = {
        'page_obj': page_obj,
        'total_orders': total_orders,
        'cancelled_count': cancelled_count,
        'total_revenue': total_revenue,
        'total_quantity': total_quantity,
        'rice_types': rice_types,
    }

    return render(request, 'allorder_history.html', context)

def payment_confirmation(request, order_id):
    # Get and clear any payment messages from session
    payment_message = request.session.pop('payment_message', None)
    payment_message_type = request.session.pop('payment_message_type', None)

    # Validate order_id is a positive integer or zero
    if not str(order_id).isdigit() or int(order_id) < 0:
        return render(request, 'payment_confirmation.html', {
            'orders': [],
            'error_message': 'Invalid order ID.'
        })

    order_id = int(order_id)

    if order_id == 0:
        # Get all orders first for debugging
        all_orders = CustomerOrder.objects.all()
        print(f"Total orders in database: {all_orders.count()}")

        # Show orders where:
        # 1. Order is active
        active_orders = all_orders.filter(is_active=True)
        print(f"Active orders: {active_orders.count()}")

        # 2. Status is pending
        pending_active_orders = active_orders.filter(approval_status__iexact='pending')
        print(f"Pending active orders: {pending_active_orders.count()}")

        # 3. Payment is not complete
        orders = pending_active_orders.filter(amount_paid__lt=F('total_cost'))
        print(f"Final orders (payment incomplete): {orders.count()}")

        # Print details of each order for debugging
        for order in orders:
            print(f"Order {order.order_id}: Type={order.delivery_type}, Active={order.is_active}, "
                  f"Status={order.approval_status}, Paid={order.amount_paid}, Total={order.total_cost}")

        return render(request, 'payment_confirmation.html', {
            'orders': orders,
            'payment_message': payment_message,
            'payment_message_type': payment_message_type
        })

    order = get_object_or_404(CustomerOrder, order_id=order_id)

    if request.method == "POST":
        # Check if this is a payment processing request
        if request.POST.get('process_payment') == 'true':
            try:
                amount = Decimal(request.POST.get('amount', '0'))
                payment_method = request.POST.get('payment_method')
                notes = request.POST.get('notes', '')

                # Validate amount
                if amount <= 0:
                    request.session['payment_message'] = 'Payment amount must be greater than 0.'
                    request.session['payment_message_type'] = 'error'
                    return redirect('payment_confirmation', order_id=0)

                # Update order with payment
                current_amount_paid = order.amount_paid or Decimal('0')
                order.amount_paid = current_amount_paid + amount
                
                # If payment is complete, approve the order
                if order.amount_paid >= order.total_cost:
                    order.approval_status = "confirmed"
                    
                    # For delivery orders, always set delivery_status to pending
                    if order.delivery_type.lower() == 'delivery':
                        order.delivery_status = 'pending'
                        print(f"Debug - Set delivery status to pending for order {order.order_id}")
                    
                    # Handle stock deduction
                    from .models import Stock
                    stock_qs = Stock.objects.filter(rice_type=order.rice_type)
                    if hasattr(order, 'packaging') and order.packaging:
                        stock_qs = stock_qs.filter(packaging=order.packaging)
                    stock = stock_qs.first()
                    if stock and stock.current_stock >= order.quantity:
                        stock.stock_out += order.quantity
                        stock.save()

                # Add payment method and notes if provided
                if payment_method:
                    order.payment_method = payment_method
                if notes:
                    order.notes = (order.notes or '') + f"\nPayment received: ₱{amount} via {payment_method}. {notes}"

                order.save()
                request.session['payment_message'] = f'Payment of ₱{amount} processed successfully.'
                request.session['payment_message_type'] = 'success'
                
                # If this is a delivery order and payment is complete, redirect to delivery confirmation
                if order.delivery_type.lower() == 'delivery' and order.amount_paid >= order.total_cost:
                    return redirect('delivery_confirmation', order_id=0)
                return redirect('payment_confirmation', order_id=0)

            except (InvalidOperation, ValueError) as e:
                request.session['payment_message'] = f'Invalid payment amount: {str(e)}'
                request.session['payment_message_type'] = 'error'
                return redirect('payment_confirmation', order_id=0)
            except Exception as e:
                request.session['payment_message'] = f'Error processing payment: {str(e)}'
                request.session['payment_message_type'] = 'error'
                return redirect('payment_confirmation', order_id=0)

        # Regular order confirmation
        if order.approval_status.lower() != "approved":
            # Only allow confirmation if payment is complete
            if order.amount_paid >= order.total_cost:
                # Deduct stock and increment stock_out
                from .models import Stock
                # Try to match both rice_type and packaging (if available)
                stock_qs = Stock.objects.filter(rice_type=order.rice_type)
                if hasattr(order, 'packaging') and order.packaging:
                    stock_qs = stock_qs.filter(packaging=order.packaging)
                stock = stock_qs.first()
                if stock and stock.current_stock >= order.quantity:
                    stock.stock_out += order.quantity
                    stock.save()  # current_stock auto-updates in model
                # else: optionally handle not enough stock
                order.approval_status = "confirmed"
                order.is_active = True  # Ensure it is active
                
                # For delivery orders, set delivery_status to pending
                if order.delivery_type.lower() == 'delivery':
                    order.delivery_status = 'pending'
                
                order.save()
                request.session['payment_message'] = 'Order has been confirmed successfully.'
                request.session['payment_message_type'] = 'success'
                
                # If this is a delivery order, redirect to delivery confirmation
                if order.delivery_type.lower() == 'delivery':
                    return redirect('delivery_confirmation', order_id=0)
                else:
                    return redirect('allorder_history')
            else:
                request.session['payment_message'] = 'Order cannot be approved. Payment is incomplete.'
                request.session['payment_message_type'] = 'error'
                return redirect('payment_confirmation', order_id=0)
        return redirect('allorder_history')

    # Only show the specific order if it meets our criteria
    if order.amount_paid >= order.total_cost:
        return render(request, 'payment_confirmation.html', {
            'orders': [],
            'error_message': 'Order is not eligible for confirmation. Payment is already complete.',
            'payment_message': payment_message,
            'payment_message_type': payment_message_type
        })

    return render(request, 'payment_confirmation.html', {
        'orders': [order],
        'payment_message': payment_message,
        'payment_message_type': payment_message_type
    })


from django.shortcuts import render, get_object_or_404
from django.db.models import Q

def delivery_confirmation(request, order_id=None):
    orders = None
    error_message = None
    success_message = None

    if request.method == 'POST' and order_id:
        try:
            order = get_object_or_404(CustomerOrder, order_id=order_id, delivery_type='delivery')
            print(f"Debug - Order {order_id}:")
            print(f"- Delivery Status: {order.delivery_status}")
            print(f"- Approval Status: {order.approval_status}")
            print(f"- Is Active: {order.is_active}")
            print(f"- Delivery Type: {order.delivery_type}")
            print(f"- Amount Paid: {order.amount_paid}")
            print(f"- Total Cost: {order.total_cost}")

            # Reset delivery status to pending if it's delivered but needs to be reconfirmed
            if order.delivery_status.lower() == 'delivered' and order.approval_status == 'confirmed' and order.is_active:
                order.delivery_status = 'pending'
                order.save()
                print(f"Debug - Reset delivery status to pending for order {order_id}")
            
            # Now check if it can be delivered
            if order.delivery_status.lower() == 'pending' and order.approval_status == 'confirmed' and order.is_active:
                order.delivery_status = 'delivered'
                order.save()
                print(f"Debug - Successfully marked order {order_id} as delivered")
                success_message = f"Order #{order.order_id} has been successfully confirmed for delivery!"
            else:
                error_message = f"Order is not eligible for delivery confirmation. Status: {order.delivery_status}, Approval: {order.approval_status}, Active: {order.is_active}"
        except Exception as e:
            error_message = f"Failed to update order: {e}"
            print(f"Debug - Exception: {e}")

    try:
        # Query for eligible orders
        base_query = {
            'delivery_type': 'delivery',
            'is_active': True,
            'delivery_status__iexact': 'pending',
            'approval_status': 'confirmed',
            'amount_paid__gte': F('total_cost')  # Ensure payment is complete
        }

        if order_id:
            orders = CustomerOrder.objects.filter(order_id=order_id, **base_query)
            # Debug log for specific order query
            print(f"Debug - Searching for order {order_id}")
            specific_order = CustomerOrder.objects.get(order_id=order_id)
            print(f"- Found order: {specific_order}")
            print(f"- Delivery Status: {specific_order.delivery_status}")
            print(f"- Approval Status: {specific_order.approval_status}")
            print(f"- Is Active: {specific_order.is_active}")
        else:
            orders = CustomerOrder.objects.filter(**base_query)
            # Debug log for all orders query
            print(f"Debug - Total orders found: {orders.count()}")
            for order in orders:
                print(f"Order {order.order_id}:")
                print(f"- Delivery Status: {order.delivery_status}")
                print(f"- Approval Status: {order.approval_status}")
                print(f"- Is Active: {order.is_active}")

        # Get counts for stats
        from django.utils import timezone
        from django.db.models import Sum
        import datetime

        today = timezone.now().date()
        
        pending_count = CustomerOrder.objects.filter(
            delivery_type='delivery',
            delivery_status__iexact='pending',
            approval_status='confirmed',
            is_active=True
        ).count()

        today_count = CustomerOrder.objects.filter(
            delivery_type='delivery',
            delivery_status__iexact='pending',
            approval_status='confirmed',
            created_at__date=today,
            is_active=True
        ).count()

        completed_count = CustomerOrder.objects.filter(
            delivery_type='delivery',
            delivery_status__iexact='delivered',
            is_active=True
        ).count()

        total_value = CustomerOrder.objects.filter(
            delivery_type='delivery',
            delivery_status__iexact='pending',
            approval_status='confirmed',
            is_active=True
        ).aggregate(total=Sum('total_cost'))['total'] or 0

    except Exception as e:
        error_message = f"An unexpected error occurred while fetching delivery orders: {e}"
        print(f"Debug - Exception in delivery_confirmation: {e}")
        pending_count = today_count = completed_count = 0
        total_value = 0

    return render(request, 'delivery_confirmation.html', {
        'orders': orders if orders is not None else [],
        'error_message': error_message,
        'success_message': success_message,
        'pending_count': pending_count,
        'today_count': today_count,
        'completed_count': completed_count,
        'total_value': total_value,
    })

@require_http_methods(["GET", "POST"])
def edit_customer_view(request, user_id):
    customer = get_object_or_404(Users, UserID=user_id)
    
    if request.method == "POST":
        # Update name
        customer.name.first_name = request.POST.get('first_name')
        customer.name.middle_name = request.POST.get('middle_name')
        customer.name.last_name = request.POST.get('last_name')
        customer.name.suffix = request.POST.get('suffix')
        customer.name.save()
        
        # Update address
        customer.address.house_unit_number = request.POST.get('house_unit_number')
        customer.address.building_name = request.POST.get('building_name')
        customer.address.street_name = request.POST.get('street_name')
        customer.address.barangay = request.POST.get('barangay')
        customer.address.city_municipality = request.POST.get('city_municipality')
        customer.address.province = request.POST.get('province')
        customer.address.zip_code = request.POST.get('zip_code')
        customer.address.save()
        
        # Update customer
        customer.Customer_Mobile_Number = request.POST.get('customer_mobile_number')
        customer.save()
        
        messages.success(request, 'Customer updated successfully.')
        return redirect('user_account')
    
    return render(request, 'edit_customer.html', {
        'customer': customer,
    })

@require_POST
@csrf_protect
def cancel_order(request, order_id):
    try:
        # Get the order
        order = CustomerOrder.objects.get(pk=order_id)
        
        # Update order status to cancelled
        order.approval_status = 'cancelled'
        order.delivery_status = 'cancelled'
        order.save()
        
        # Log the cancellation
        log_user_action(request.session.get('user_id'), f'Cancelled order #{order_id}')
        
        # Add success message
        messages.success(request, f'Order #{order_id} has been cancelled successfully.')
        
        # Redirect back to the appropriate page
        if request.META.get('HTTP_REFERER'):
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        return redirect('dashboard')
        
    except CustomerOrder.DoesNotExist:
        messages.error(request, f'Order #{order_id} not found.')
        return redirect('dashboard')
    except Exception as e:
        messages.error(request, f'Error cancelling order: {str(e)}')
        return redirect('dashboard')
