from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from . import analysis
from .errors import NoRouteError, ProviderError
from .providers import geocode
from .serializers import AnalyzeSerializer


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


class GeocodeView(APIView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if len(q) < 3:
            return Response({"results": []})
        try:
            return Response({"results": geocode.search(q)})
        except ProviderError as exc:
            return Response({"error": str(exc)}, status=502)


class AnalyzeView(APIView):
    def post(self, request):
        serializer = AnalyzeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        try:
            payload = analysis.analyze(
                (d["origin"]["lat"], d["origin"]["lng"]),
                (d["destination"]["lat"], d["destination"]["lng"]),
                d["departure"],
                d["load_lb"],
                int(d["interval_mi"]),
            )
        except NoRouteError:
            return Response({"error": "No drivable route found between those two places."}, status=422)
        except ProviderError as exc:
            return Response({"error": str(exc)}, status=502)
        payload["request"]["origin"] = d["origin"]
        payload["request"]["destination"] = d["destination"]
        return Response(payload)
