# Management command to seed demo data

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from core.models import Notification
from core.notifications import project_member_added, task_assigned
from projects.models import Project, ProjectMembership
from tasks.models import Task


DEMO_EMAILS = [
    'alex@stride.test',
    'jamie@stride.test',
    'morgan@stride.test',
    'sam@stride.test',
    'taylor@stride.test',
]

DEMO_PASSWORD = 'stride123'


class Command(BaseCommand):
    help = 'Seed the database with demo accounts, projects, tasks, and notifications.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing demo accounts and their data before seeding.',
        )

    def handle(self, *args, **options):
        reset = options.get('reset', False)

        if reset:
            Project.objects.filter(owner__email__in=DEMO_EMAILS).delete()
            User.objects.filter(email__in=DEMO_EMAILS).delete()
            self.stdout.write('Removed existing demo accounts.')

        if User.objects.filter(email__in=DEMO_EMAILS).exists():
            self.stdout.write(self.style.WARNING(
                'Demo accounts already exist. Use --reset to recreate.'
            ))
            return

        self.stdout.write('Creating demo accounts...')
        users = self._create_users()

        self.stdout.write('Creating projects, tasks, and notifications...')
        project_ids, task_ids, notification_ids = self._create_content(users)

        self._verify(users, project_ids, task_ids, notification_ids)

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully.'))
        self._print_summary(users, project_ids, task_ids, notification_ids)

    def _create_users(self):
        users = {}
        for key, first, last in (
            ('alex', 'Alex', 'Lee'),
            ('jamie', 'Jamie', 'Kim'),
            ('morgan', 'Morgan', 'Shah'),
            ('sam', 'Sam', 'Patel'),
            ('taylor', 'Taylor', 'Reed'),
        ):
            users[key] = User.objects.create_user(
                email=f'{key}@stride.test',
                password=DEMO_PASSWORD,
                first_name=first,
                last_name=last,
                is_active=True,
            )
        return users

    def _create_content(self, users):
        from core.notifications import project_member_added, task_assigned

        now = timezone.now()
        today = timezone.localdate()

        PROJECT_SPECS = [
            {
                'title': 'Product Launch',
                'owner': 'alex',
                'admins': ['jamie'],
                'members': ['jamie', 'morgan', 'sam', 'taylor'],
                'due': 12,
                'description': 'Bring the next Stride release to market with a clear launch plan, polished onboarding, and reliable tracking.',
                'tasks': [
                    ('todo', 'Plan launch-day checklist', 'Map the release steps, owners, and rollback checks so the team knows what happens on launch day.', 'high', 'alex', 3),
                    ('todo', 'Prepare customer announcement', 'Draft the launch email and in-app announcement with a clear summary of what is new.', 'medium', 'sam', 5),
                    ('todo', 'Collect final product screenshots', 'Capture the dashboard, task board, and notification dropdown for the launch materials.', 'low', None, 6),
                    ('in_progress', 'Finish onboarding flow', 'Make the first-project experience clear and confirm new users can create their first task.', 'high', 'jamie', 1),
                    ('in_progress', 'Resolve checkout payment failure', 'Investigate the failed-payment retry path and verify customers are not charged twice.', 'critical', 'morgan', -2),
                    ('in_progress', 'Coordinate launch partners', 'Confirm partner publication dates and share the final launch assets.', 'medium', 'taylor', 2),
                    ('review', 'Review homepage launch copy', 'Check the final headline, product benefits, and calls to action before publishing.', 'medium', 'sam', 0),
                    ('review', 'Approve product demo video', 'Review the walkthrough for accuracy, pacing, and readable captions.', 'high', 'alex', -1),
                    ('review', 'Verify analytics events', 'Check signup, project creation, and task-completion events in the release environment.', 'medium', 'morgan', 2),
                    ('completed', 'Define launch milestones', 'Agree on the release checklist, owners, and acceptance criteria.', 'high', 'alex', -5),
                    ('completed', 'Publish internal release notes', 'Document the changes and known limitations for the support team.', 'low', 'jamie', -3),
                    ('completed', 'Set up launch tracking board', 'Organize launch work into clear statuses and assign the initial owners.', 'medium', 'taylor', -4),
                ],
            },
            {
                'title': 'Website Redesign',
                'owner': 'jamie',
                'admins': ['alex'],
                'members': ['alex', 'morgan', 'taylor'],
                'due': 18,
                'description': 'Refresh the marketing website with responsive layouts, accessible interactions, and a faster signup experience.',
                'tasks': [
                    ('todo', 'Design pricing comparison section', 'Create a simple comparison of the plans with clear limits and upgrade actions.', 'medium', 'morgan', 7),
                    ('todo', 'Audit existing page content', 'Identify outdated screenshots, duplicate sections, and copy that no longer matches the product.', 'low', 'taylor', 4),
                    ('todo', 'Write accessibility acceptance criteria', 'Define keyboard, focus, contrast, and screen-reader checks for the redesigned pages.', 'high', 'alex', 3),
                    ('in_progress', 'Build responsive navigation', 'Implement desktop and mobile navigation with consistent active states and keyboard support.', 'high', 'jamie', 0),
                    ('in_progress', 'Optimize landing-page images', 'Resize large assets, choose efficient formats, and prevent layout shifts while images load.', 'medium', 'taylor', -3),
                    ('in_progress', 'Implement signup validation', 'Make field errors clear and preserve valid input when a signup attempt fails.', 'high', 'alex', 2),
                    ('review', 'Review mobile spacing', 'Check card padding, section gaps, and text wrapping on small screens.', 'medium', 'morgan', 1),
                    ('review', 'Check keyboard navigation', 'Confirm all interactive elements have visible focus and a predictable tab order.', 'high', 'alex', -1),
                    ('review', 'Approve updated brand palette', 'Review the final color tokens against the existing forest-green identity.', 'low', 'jamie', 2),
                    ('completed', 'Map the new site structure', 'Agree on the page hierarchy and the primary path from discovery to signup.', 'medium', 'taylor', -7),
                    ('completed', 'Create typography tokens', 'Standardize the heading, body, and supporting-text styles.', 'medium', 'morgan', -5),
                    ('completed', 'Remove unused page sections', 'Retire outdated blocks while preserving the useful product information.', 'low', 'jamie', -4),
                ],
            },
            {
                'title': 'Mobile App',
                'owner': 'morgan',
                'admins': ['alex'],
                'members': ['alex', 'jamie', 'sam'],
                'due': 21,
                'description': 'Prepare the mobile experience for release, with stable sign-in, offline behavior, and layouts that work on phones and tablets.',
                'tasks': [
                    ('todo', 'Plan offline sync conflict handling', 'Define what happens when the same task changes on multiple devices while offline.', 'high', 'sam', 6),
                    ('todo', 'Draft app store release notes', 'Summarize the release improvements in short, customer-friendly language.', 'low', 'jamie', 5),
                    ('todo', 'Triage next-sprint improvements', 'Group the latest feedback and choose a small set of high-impact improvements.', 'medium', None, 7),
                    ('in_progress', 'Fix Android sign-in crash', 'Reproduce the crash after session expiry and verify the return-to-login flow.', 'critical', 'morgan', -1),
                    ('in_progress', 'Implement task detail screen', 'Show task information with clear editing controls and reliable save feedback.', 'high', 'alex', 1),
                    ('in_progress', 'Polish permission onboarding', 'Explain optional permissions clearly and keep the main workflow usable when permission is declined.', 'medium', 'sam', 3),
                    ('review', 'Validate iOS notification badges', 'Check unread counts after opening notifications and switching between sessions.', 'high', 'jamie', 0),
                    ('review', 'Review offline cache behavior', 'Confirm cached tasks remain readable and that updates reconcile when connectivity returns.', 'high', 'sam', -2),
                    ('review', 'Check tablet board layout', 'Review column widths, horizontal scrolling, and task-card readability on tablets.', 'medium', 'alex', 2),
                    ('completed', 'Set up mobile build pipeline', 'Create a repeatable build process and record the release steps.', 'high', 'morgan', -8),
                    ('completed', 'Create navigation shell', 'Build the primary navigation and establish shared screen layout components.', 'medium', 'alex', -6),
                    ('completed', 'Add secure session storage', 'Store session state using the platform storage mechanism and clear it on logout.', 'high', 'sam', -4),
                ],
            },
        ]

        project_ids = []
        task_ids = []
        notification_ids = []

        for spec in PROJECT_SPECS:
            owner = users[spec['owner']]
            project = Project.objects.create(
                owner=owner,
                title=spec['title'],
                description=spec['description'],
                deadline=today + timedelta(days=spec['due']),
            )
            project_ids.append(project.pk)

            for key in spec['members']:
                membership = ProjectMembership.objects.create(
                    project=project,
                    user=users[key],
                    role='admin' if key in spec['admins'] else 'member',
                )
                project_member_added(membership, owner)
                item = Notification.objects.get(
                    recipient=users[key], project=project, kind='project_added'
                )
                notification_ids.append(item.pk)

            positions = {}
            for idx, (status, title, description, priority, assignee, due) in enumerate(spec['tasks']):
                task = Task.objects.create(
                    project=project,
                    created_by=owner,
                    assigned_to=users[assignee] if assignee else None,
                    title=title,
                    description=description,
                    status=status,
                    priority=priority,
                    deadline=today + timedelta(days=due),
                    position=positions.get(status, 0),
                )
                positions[status] = positions.get(status, 0) + 1
                task_ids.append(task.pk)

                task_assigned(task, owner)
                item = Notification.objects.filter(task=task).first()
                if item:
                    notification_ids.append(item.pk)

        return project_ids, task_ids, notification_ids

    def _verify(self, users, project_ids, task_ids, notification_ids):
        assert Project.objects.filter(pk__in=project_ids).count() == 3
        assert Task.objects.filter(pk__in=task_ids).count() == 36
        for user in users.values():
            assert authenticate(username=user.email, password=DEMO_PASSWORD) is not None
            assert not user.is_staff and not user.is_superuser
        for task in Task.objects.filter(pk__in=task_ids):
            task.full_clean()
            assert (task.completed_at is not None) == (task.status == 'completed')

    def _print_summary(self, users, project_ids, task_ids, notification_ids):
        from collections import Counter
        self.stdout.write('\n--- Demo accounts (password: stride123) ---')
        for user in users.values():
            self.stdout.write(f'  {user.email}  —  {user.get_full_name()}')
        self.stdout.write(f'\nProjects: {len(project_ids)}')
        self.stdout.write(f'Tasks: {len(task_ids)}')
        self.stdout.write(f'Notifications: {len(notification_ids)}')
        self.stdout.write(f'Memberships: {ProjectMembership.objects.filter(project_id__in=project_ids).count()}')
        overdue = Task.objects.filter(pk__in=task_ids, deadline__lt=timezone.localdate()).exclude(status='completed').count()
        self.stdout.write(f'Overdue tasks: {overdue}')


if __name__ == '__main__':
    import sys
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)