from django.apps import AppConfig

class LimpiezaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'limpieza'
    
    def ready(self):
        # Crear permisos por defecto
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from django.db.models.signals import post_migrate
        
        def create_permissions(sender, **kwargs):
            content_type = ContentType.objects.get_for_model(self.get_model('OperacionLimpieza'))
            
            Permission.objects.get_or_create(
                codename='can_clean_data',
                name='Puede limpiar datos',
                content_type=content_type,
            )
            
            Permission.objects.get_or_create(
                codename='can_view_stats',
                name='Puede ver estadísticas',
                content_type=content_type,
            )
        
        post_migrate.connect(create_permissions, sender=self)