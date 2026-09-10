import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .app import build_dashboard, predict_student


def _public_dashboard_data():
    data = build_dashboard()
    return {k: v for k, v in data.items() if not k.startswith("_")}


def dashboard(request):
    return render(request, "dashboard.html")


@require_GET
def dashboard_api(request):
    try:
        return JsonResponse(_public_dashboard_data())
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@require_POST
def predict_enrollment(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        return JsonResponse(predict_student(payload))
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=400)
