from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        """
        Inicialização quando a aplicação está pronta
        """
        # Importar signals
        try:
            import core.signals
        except ImportError:
            pass
        
        # Registrar MCP tools - DISABLED for Docker compatibility
        # try:
        #     self.register_mcp_tools()
        # except ImportError:
        #     # django-mcp-server não instalado ou não disponível
        #     pass
    
    def register_mcp_tools(self):
        """Registra ferramentas MCP do projeto"""
        from mcp_server import mcp_server
        from .mcp_tools import ALL_MCP_TOOLSETS, ALL_MCP_TOOLS
        
        # Registrar ModelQueryToolsets
        for toolset_class in ALL_MCP_TOOLSETS:
            try:
                toolset_instance = toolset_class()
                mcp_server.register_mcptoolset(toolset_instance)
                print(f"[MCP] Registered toolset: {toolset_class.__name__}")
            except Exception as e:
                print(f"[MCP] Failed to register toolset {toolset_class.__name__}: {e}")
        
        # Registrar ferramentas customizadas
        for tool_class in ALL_MCP_TOOLS:
            try:
                tool_instance = tool_class()
                # Tentar diferentes métodos de registro
                if hasattr(mcp_server, 'add_tool'):
                    mcp_server.add_tool(tool_instance)
                elif hasattr(mcp_server, 'tool'):
                    mcp_server.tool(tool_instance.get_name())(tool_instance.execute)
                print(f"[MCP] Registered tool: {tool_class.__name__}")
            except Exception as e:
                print(f"[MCP] Failed to register tool {tool_class.__name__}: {e}")
