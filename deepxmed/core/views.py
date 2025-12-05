from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def index(request):
    # Always show landing page first
    return render(request, 'core/index.html')

@login_required
def home(request):
    return render(request, 'core/home.html')
