
// Registry #88 assessment-only overlay. Never published to VTI.
#[tokio::test]
async fn registry_88_nested_critical_extensions() {
    const REGISTER: &str = "https://trusttasks.org/spec/vtc/schemas/accepts/register/0.2";
    const STATEMENT: &str = "https://example.test/predicates/vetted/1";
    let mut fix = fixture(true).await;
    let a = requester(&mut fix).await;
    for (task, body) in [
        ("https://trusttasks.org/spec/vtc/schemas/register/0.1",
         json!({"typeUri":"Vetted","kind":"accepts"})),
        ("https://trusttasks.org/spec/vtc/endorsement-types/register/0.1",
         json!({"typeUri":STATEMENT,"description":"A member vetted this person"})),
    ] {
        let doc = signed(&a, task, body).await;
        let (status, reply) = submit(&mut fix, &a, &doc).await;
        assert_eq!(status, StatusCode::OK, "prerequisite {task}: {reply}");
    }
    let mut deviations = Vec::new();
    for (id, ext, critical, expected) in [
        ("control", None, None, None),
        ("noncritical", Some(json!({"org.example.unknown":true})), None, None),
        ("unknown", Some(json!({"org.example.unknown":true})), Some(json!(["org.example.unknown"])), Some("unsupportedExtension")),
        ("missing-ext", None, Some(json!(["org.example.unknown"])), Some("malformedRequest")),
        ("missing-name", Some(json!({"org.example.other":true})), Some(json!(["org.example.unknown"])), Some("malformedRequest")),
        ("duplicate", Some(json!({"org.example.unknown":true})), Some(json!(["org.example.unknown","org.example.unknown"])), Some("malformedRequest")),
    ] {
        let mut body = json!({
            "id":id,"admission":"review","credentialIssuers":"any",
            "query":{"credentials":[{"id":"c","format":"dc+sd-jwt","meta":{"vct_values":["Vetted"]}}]},
            "vetting":{"version":"0.1","statementType":STATEMENT,"minStatements":1,
                "minByMethod":{},"acceptedMethods":["video"],"eligibleVetters":{"role":"vetter"}}
        });
        if let Some(value) = ext { body["vetting"]["ext"] = value; }
        if let Some(value) = critical { body["vetting"]["extCritical"] = value; }
        assert!(vtc_service::schemas::get_accepts(&fix.vtc.state.schemas_ks,id).await.unwrap().is_none());
        let doc = signed(&a, REGISTER, body).await;
        // Observe the first response separately: a consent gate is not
        // critical-extension enforcement. In the isolated fixture satisfy
        // any requested gesture to observe the ultimate consequential effect.
        let (first_status, first) = post(&fix.vtc, &doc).await;
        let gesture = step_up_request(&first).is_some();
        let (status, reply) = if gesture {
            fix.gesturer.gesture(&fix.vtc, &a, &first).await;
            post(&fix.vtc, &doc).await
        } else { (first_status, first.clone()) };
        let stored = vtc_service::schemas::get_accepts(&fix.vtc.state.schemas_ks,id).await.unwrap().is_some();
        let code = reply["payload"]["code"].as_str();
        println!("REGISTRY88 {id} first={first_status} gesture={gesture} final={status} code={code:?} stored={stored}");
        if let Some(expected) = expected {
            let (retry_status, retry) = post(&fix.vtc, &doc).await;
            let retry_stored = vtc_service::schemas::get_accepts(&fix.vtc.state.schemas_ks,id).await.unwrap().is_some();
            println!("REGISTRY88 {id} retry={retry_status} code={:?} stored={retry_stored}", retry["payload"]["code"]);
            if gesture || status.is_success() || code != Some(expected) || stored ||
                retry_status.is_success() || retry["payload"]["code"].as_str() != Some(expected) || retry_stored {
                deviations.push(id);
            }
        } else {
            assert!(gesture && status.is_success() && stored, "positive control {id}: {reply}");
        }
    }
    assert!(deviations.is_empty(), "critical-extension deviations: {deviations:?}");
}
