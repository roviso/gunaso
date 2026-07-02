from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.organizations.models import Organization
from apps.submissions.models import Category, Submission, StatusUpdate

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with sample organizations, users, and submissions.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING('\n========================================'))
        self.stdout.write(self.style.MIGRATE_HEADING('  Gunaso API - Seeding Sample Data'))
        self.stdout.write(self.style.MIGRATE_HEADING('========================================\n'))

        users = self._create_users()
        orgs = self._create_organizations(users)
        categories = self._create_categories(orgs)
        self._create_submissions(users, orgs, categories)
        self._create_superuser()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('DONE  Seeding complete!\n'))
        self.stdout.write('  Login credentials:')
        self.stdout.write('  -------------------------------------------------')
        self.stdout.write('  citizen@gmail.com          / password123  (citizen)')
        self.stdout.write('  admin@nepaltel.com         / password123  (org_admin)')
        self.stdout.write('  admin@kmcity.gov.np        / password123  (org_admin)')
        self.stdout.write('  admin@nmbbank.com.np       / password123  (org_admin)')
        self.stdout.write('  superadmin@gunaso.com      / admin123     (superuser)')
        self.stdout.write('  -------------------------------------------------')
        self.stdout.write('  Admin panel: http://localhost:8000/admin/')
        self.stdout.write('  API root:    http://localhost:8000/api/v1/\n')

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def _create_users(self):
        self.stdout.write('  Creating users...')

        citizen = self._upsert_user(
            username='citizen_ram',
            email='citizen@gmail.com',
            password='password123',
            first_name='Ram',
            last_name='Sharma',
            user_type='citizen',
        )

        admin1 = self._upsert_user(
            username='admin_nepaltel',
            email='admin@nepaltel.com',
            password='password123',
            first_name='Suresh',
            last_name='Pradhan',
            user_type='org_admin',
        )

        admin2 = self._upsert_user(
            username='admin_kmcity',
            email='admin@kmcity.gov.np',
            password='password123',
            first_name='Sita',
            last_name='Rai',
            user_type='org_admin',
        )

        admin3 = self._upsert_user(
            username='admin_nmb',
            email='admin@nmbbank.com.np',
            password='password123',
            first_name='Rajesh',
            last_name='Thapa',
            user_type='org_admin',
        )

        self.stdout.write(self.style.SUCCESS('    OK 4 users ready'))
        return {'citizen': citizen, 'admin1': admin1, 'admin2': admin2, 'admin3': admin3}

    def _upsert_user(self, username, email, password, first_name, last_name, user_type):
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'user_type': user_type,
            },
        )
        user.set_password(password)
        user.save()
        return user

    # ------------------------------------------------------------------
    # Organizations
    # ------------------------------------------------------------------

    def _create_organizations(self, users):
        self.stdout.write('  Creating organizations...')

        org1, _ = Organization.objects.get_or_create(
            slug='nepal-telecom',
            defaults={
                'name': 'Nepal Telecom',
                'description': 'State-owned telecommunications company of Nepal, providing internet, phone, and data services nationwide.',
                'category': 'telecom',
                'contact_email': 'support@ntc.net.np',
                'website': 'https://www.ntc.net.np',
                'is_verified': True,
                'admin': users['admin1'],
            },
        )

        org2, _ = Organization.objects.get_or_create(
            slug='kathmandu-municipality',
            defaults={
                'name': 'Kathmandu Metropolitan City',
                'description': 'Municipal government responsible for city services, infrastructure, waste management, and urban development in Kathmandu.',
                'category': 'government',
                'contact_email': 'info@kathmandu.gov.np',
                'website': 'https://kathmandu.gov.np',
                'is_verified': True,
                'admin': users['admin2'],
            },
        )

        org3, _ = Organization.objects.get_or_create(
            slug='nmb-bank',
            defaults={
                'name': 'NMB Bank',
                'description': 'A leading commercial bank in Nepal offering retail banking, loans, digital banking, and investment services.',
                'category': 'bank',
                'contact_email': 'info@nmbbank.com.np',
                'website': 'https://nmbbank.com.np',
                'is_verified': True,
                'admin': users['admin3'],
            },
        )

        self.stdout.write(self.style.SUCCESS('    OK 3 organizations ready'))
        return {'org1': org1, 'org2': org2, 'org3': org3}

    # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------

    def _create_categories(self, orgs):
        self.stdout.write('  Creating categories...')
        org1, org2, org3 = orgs['org1'], orgs['org2'], orgs['org3']

        cats = {}
        pairs = [
            ('ntc_network', 'Network Issues', org1),
            ('ntc_billing', 'Billing', org1),
            ('ntc_service', 'Customer Service', org1),
            ('kmc_road', 'Road & Infrastructure', org2),
            ('kmc_waste', 'Waste Management', org2),
            ('kmc_permits', 'Permits & Licenses', org2),
            ('nmb_loans', 'Loan Services', org3),
            ('nmb_atm', 'ATM Issues', org3),
            ('nmb_mobile', 'Mobile Banking', org3),
        ]
        for key, name, org in pairs:
            cat, _ = Category.objects.get_or_create(name=name, organization=org)
            cats[key] = cat

        self.stdout.write(self.style.SUCCESS('    OK 9 categories ready'))
        return cats

    # ------------------------------------------------------------------
    # Submissions
    # ------------------------------------------------------------------

    def _create_submissions(self, users, orgs, cats):
        self.stdout.write('  Creating submissions...')
        citizen = users['citizen']
        org1, org2, org3 = orgs['org1'], orgs['org2'], orgs['org3']
        year = timezone.now().year
        existing = Submission.objects.count()

        records = [
            dict(
                organization=org1, category=cats['ntc_network'],
                citizen=citizen, citizen_name='Ram Sharma',
                citizen_email='citizen@gmail.com', citizen_phone='9801234567',
                submission_type='complaint', priority='high', status='in_review',
                title='Fiber internet down for 3 consecutive days',
                description='My fiber internet connection has been completely down for 3 days. I work from home and this is causing serious productivity losses. I have already called the helpline but no resolution has been provided.',
            ),
            dict(
                organization=org1, category=cats['ntc_billing'],
                citizen=citizen, citizen_name='Ram Sharma',
                citizen_email='citizen@gmail.com', citizen_phone='9801234567',
                submission_type='complaint', priority='medium', status='acknowledged',
                title='Incorrect billing - overcharged by Rs 2,000',
                description='My monthly bill for March 2024 shows Rs 2,000 more than my regular plan amount. No additional services were activated. Please investigate and issue a refund.',
            ),
            dict(
                organization=org2, category=cats['kmc_road'],
                citizen=None, citizen_name='Anonymous Citizen',
                citizen_email='anon@placeholder.com', citizen_phone='',
                submission_type='complaint', priority='urgent', status='submitted',
                is_anonymous=True,
                title='Large pothole causing accidents at Baneshwor chowk',
                description='There is a dangerous pothole near Baneshwor chowk that has caused at least 2 motorbike accidents this week. Immediate repair is needed before more people get hurt.',
            ),
            dict(
                organization=org2, category=cats['kmc_waste'],
                citizen=citizen, citizen_name='Ram Sharma',
                citizen_email='citizen@gmail.com', citizen_phone='9801234567',
                submission_type='complaint', priority='high', status='resolved',
                title='Garbage not collected for 2 weeks in Koteshwor',
                description='The waste collection truck has not visited our area (Koteshwor ward 32) for two weeks. The garbage is overflowing and creating a health hazard for residents.',
            ),
            dict(
                organization=org3, category=cats['nmb_atm'],
                citizen=citizen, citizen_name='Ram Sharma',
                citizen_email='citizen@gmail.com', citizen_phone='9801234567',
                submission_type='complaint', priority='urgent', status='escalated',
                title='ATM swallowed my card at New Road branch',
                description='The NMB ATM at the New Road branch retained my card during a withdrawal attempt. The machine showed a timeout error and did not return the card. I called customer service but was put on hold for 45 minutes with no resolution.',
            ),
            dict(
                organization=org1, category=cats['ntc_service'],
                citizen=citizen, citizen_name='Ram Sharma',
                citizen_email='citizen@gmail.com', citizen_phone='9801234567',
                submission_type='feedback', priority='low', status='closed',
                title='Excellent customer service from helpline agent',
                description='I want to commend the support agent (ticket #NTC-5521) who helped resolve my connection issue within 30 minutes. Very professional and patient. Keep up the great work!',
            ),
            dict(
                organization=org2, category=cats['kmc_permits'],
                citizen=citizen, citizen_name='Ram Sharma',
                citizen_email='citizen@gmail.com', citizen_phone='9801234567',
                submission_type='suggestion', priority='medium', status='acknowledged',
                title='Implement online permit application portal',
                description='The current physical queue system for building permits is extremely time-consuming. An online application system would reduce wait times from days to hours and reduce corruption opportunities.',
            ),
            dict(
                organization=org3, category=cats['nmb_mobile'],
                citizen=citizen, citizen_name='Ram Sharma',
                citizen_email='citizen@gmail.com', citizen_phone='9801234567',
                submission_type='complaint', priority='medium', status='in_review',
                title='NMB Smart app shows authentication failed on every login',
                description='Since the app update on 2024-03-10, I cannot log into the NMB Smart banking app. It shows "Authentication failed. Please try again." every time. I have uninstalled and reinstalled but the issue persists.',
            ),
            dict(
                organization=org1, category=cats['ntc_network'],
                citizen=None, citizen_name='Pramod Koirala',
                citizen_email='pramod@example.com', citizen_phone='9807654321',
                submission_type='complaint', priority='high', status='submitted',
                title='Speed consistently below 10 Mbps on 100 Mbps plan',
                description='I pay for the 100 Mbps fiber plan but speed tests consistently show 8–12 Mbps. This has been the case for the past month. I have tested with multiple devices and the issue is not on my end.',
            ),
            dict(
                organization=org2, category=cats['kmc_road'],
                citizen=None, citizen_name='Gita Thapa',
                citizen_email='gita.thapa@example.com', citizen_phone='9812345678',
                submission_type='suggestion', priority='medium', status='acknowledged',
                title='Install pedestrian crossing at Chabahil junction',
                description='The Chabahil junction has very high foot traffic but no safe pedestrian crossing. A zebra crossing with proper signage or a footbridge would significantly reduce accident risk for pedestrians.',
            ),
        ]

        created = 0
        for i, data in enumerate(records):
            is_anon = data.pop('is_anonymous', False)
            ref = f'GUN-{year}-{(existing + i + 1):05d}'
            if not Submission.objects.filter(reference_number=ref).exists():
                Submission.objects.create(reference_number=ref, is_anonymous=is_anon, **data)
                created += 1

        self.stdout.write(self.style.SUCCESS(f'    OK {created} submissions created'))

    # ------------------------------------------------------------------
    # Superuser
    # ------------------------------------------------------------------

    def _create_superuser(self):
        self.stdout.write('  Creating superuser...')
        if not User.objects.filter(username='superadmin').exists():
            User.objects.create_superuser(
                username='superadmin',
                email='superadmin@gunaso.com',
                password='admin123',
            )
            self.stdout.write(self.style.SUCCESS('    OK Superuser created'))
        else:
            self.stdout.write('    OK Superuser already exists')
