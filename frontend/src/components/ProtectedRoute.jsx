import { Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

export default function ProtectedRoute({ token, user, allowedRoles, effectiveRole, children }) {
 const { t } = useTranslation()
 if (!token) return <Navigate to="/login" replace />
 if (!user) return <div className="container">{t('common.loading')}</div>
 if (allowedRoles && !allowedRoles.includes(effectiveRole || user.role)) return <Navigate to="/" replace />
 return children
}
