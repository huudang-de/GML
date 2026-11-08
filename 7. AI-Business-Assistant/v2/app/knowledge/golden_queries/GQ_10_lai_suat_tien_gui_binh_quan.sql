SELECT SUM(original_amount * interest_rate) / NULLIF(SUM(original_amount), 0)
FROM ai_views.ai_v_tien_gui
WHERE is_active_at_cutoff = TRUE;
