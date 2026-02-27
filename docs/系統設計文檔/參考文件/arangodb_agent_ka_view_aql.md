// ============================================================
// ArangoDB View: agent_ka_view
// ============================================================

// Step 1: Create ArangoSearch View
// Run this in ArangoDB Web UI (AQL Editor) or arangosh

CREATE ARANGOSEARCH VIEW agent_ka_view OPTIONS {
  consolidationIntervalMsec: 60000,
  commitIntervalMsec: 1000
}


// Step 2: Link collection to view
// Run this after creating the view

FOR v IN agent_ka_view
  UPDATE v WITH {
    links: {
      kb_agent_authorization: {
        fields: {
          agent_key: { analyzers: ["identity"], includeAllFields: false },
          agent_id: { analyzers: ["identity"], includeAllFields: false },
          kb_root_key: { analyzers: ["identity"], includeAllFields: false },
          folder_key: { analyzers: ["identity"], includeAllFields: false },
          file_id: { analyzers: ["identity"], includeAllFields: false },
          file_name: { analyzers: ["identity"], includeAllFields: false }
        },
        storeValues: "id",
        trackListPositions: false
      }
    }
  } IN agent_ka_view


// ============================================================
// Query Examples
// ============================================================

// Query all files for agent -h0tjyh
FOR doc IN agent_ka_view
  FILTER doc.agent_key == "-h0tjyh"
  RETURN doc.file_name

// Query by agent_id
FOR doc IN agent_ka_view
  FILTER doc.agent_id == "mm-agent"
  RETURN doc.file_name

// Full-text search on file names (if Chinese analyzer exists)
FOR doc IN agent_ka_view
  SEARCH ANALYZER(doc.file_name IN TOKENS("物料管理", "textzh"), "textzh")
  RETURN doc.file_name


// ============================================================
// Alternative: Using arangosh command line
// ============================================================

/*
# Create view
arangosh --server.database=ai_box_kg --server.username=root --server.password=xxx \
  --eval "db._createView('agent_ka_view', 'arangosearch', {consolidationIntervalMsec: 60000})"

# Link collection (using AQL in arangosh)
arangosh --server.database=ai_box_kg --server.username=root --server.password=xxx \
  --eval "db.agent_ka_view.properties({links: {kb_agent_authorization: {fields: {agent_key: {analyzers: ['identity']}}}}})"
*/
