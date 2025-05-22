from webapp.models import Employee, Users, UserName

def sync_employees_to_users():
    created = 0
    for emp in Employee.objects.all():
        if not Users.objects.filter(Username=emp.Username).exists():
            # Create UserName object for the Users.name field
            user_name_obj = UserName.objects.create(
                first_name=emp.FirstName,
                middle_name=emp.MiddleName,
                last_name=emp.LastName,
                suffix=emp.Suffix
            )
            # Generate a unique email for this user
            email = f"{emp.Username}@autogen.local"
            Users.objects.create(
                Username=emp.Username,
                Password=emp.Password,  # You may want to hash this or set a default
                name=user_name_obj,
                Role='employee',
                Acc_Status='active',
                Email=email,
            )
            created += 1
    print(f"Created {created} missing Users accounts.")

if __name__ == "__main__":
    sync_employees_to_users()
