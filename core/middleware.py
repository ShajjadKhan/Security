from django.shortcuts import redirect
from django.urls import reverse
from core.models import Property

class SubscriptionEnforcementMiddleware:
    """
    SaaS Subscription Access Enforcement Middleware:
    Locks operational access (gates, visitors, gatepasses, lost & found)
    if the client property's subscription status is 'suspended'.
    Platform owner (vendor) and superusers are exempt.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if not (request.user.is_superuser or getattr(request.user, 'role', '') == 'saas_owner'):
                path = request.path
                exempt_paths = [
                    reverse('subscription_suspended'),
                    reverse('logout'),
                    reverse('set_language'),
                ]
                if not any(path.startswith(p) for p in exempt_paths) and not path.startswith('/static/') and not path.startswith('/media/'):
                    prop_id = request.session.get('current_property_id')
                    prop = None
                    if prop_id and prop_id != 'ALL':
                        prop = Property.objects.filter(id=prop_id).first()
                    if not prop and getattr(request.user, 'assigned_property', None):
                        prop = request.user.assigned_property

                    if prop and prop.subscription_status == 'suspended':
                        return redirect('subscription_suspended')

        response = self.get_response(request)
        return response
