"""Protected routes; distinct from the deliberately public NASA hackathon demo."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from .review import MissionReviewRequest, build_review
from .review_pdf import make_decision_pdf, latex_decision_report
from .security import WorkspaceIdentity, require_workspace_identity, record_report_export

router = APIRouter(prefix='/api/private', tags=['private-workspace'])

@router.get('/whoami')
def whoami(identity: WorkspaceIdentity = Depends(require_workspace_identity)):
    return {'user_id':identity.user_id,'name':identity.verified_name,'role':identity.role,
            'mfa':'verified','source':'server-managed operator directory'}

@router.post('/mission-review')
def private_review(request: MissionReviewRequest,
                   identity: WorkspaceIdentity = Depends(require_workspace_identity)):
    result = build_review(request)
    result['prepared_by'] = identity.verified_name
    result['prepared_by_id'] = identity.user_id
    return result

@router.post('/mission-decision/{kind}.{fmt}')
def private_export(kind: str, fmt: str, request: MissionReviewRequest,
                   identity: WorkspaceIdentity = Depends(require_workspace_identity)):
    if kind not in ('brief', 'dossier') or fmt not in ('pdf', 'tex', 'json'):
        raise HTTPException(status_code=404, detail='Unknown report format')
    result = build_review(request)  # engine recomputes; no user-provided result accepted
    result['prepared_by'] = identity.verified_name
    result['prepared_by_id'] = identity.user_id
    ref = record_report_export(identity, result, kind + '.' + fmt)
    result['audit_id'] = ref
    if fmt == 'json':
        return result
    if fmt == 'tex':
        payload = latex_decision_report(result, kind).encode('utf-8')
        mime = 'application/x-tex'
    else:
        payload, _ = make_decision_pdf(result, kind, prefer_latex=False)
        mime = 'application/pdf'
    return Response(content=payload, media_type=mime,
                    headers={'Content-Disposition':f'attachment; filename="POLARIS_{result["review_id"]}_{kind}.{fmt}"',
                             'X-POLARIS-REVIEW-ID':result['review_id'],
                             'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
