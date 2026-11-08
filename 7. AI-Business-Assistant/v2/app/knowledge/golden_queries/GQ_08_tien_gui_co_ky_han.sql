SELECT SUM(original_amount)
FROM ai_views.ai_v_tien_gui
WHERE is_active_at_cutoff = TRUE;
