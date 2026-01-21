user_id = 8
emp = env['hr.employee'].search([('fingerprint_user_id', '=', user_id)])

if emp:
    print(f"User {user_id} maps to: {emp.name}")
    # Cleanup logs and attendance
    logs = env['onedrive.attendance'].search([('user_id', '=', user_id)])
    logs.unlink()
    atts = env['hr.attendance'].search([('employee_id', '=', emp.id)])
    atts.unlink()
    env.cr.commit()
    print("Cleaned up User 8.")

    test_logs = [
        # Day 1: Burst "I" Only. First In (8:00) -> Last Activity (8:05)
        ('2026-01-22 08:00:00', 'I'),
        ('2026-01-22 08:01:00', 'I'),
        ('2026-01-22 08:05:00', 'I'),

        # Day 2: Mixed "I" and "O". First In (08:00) -> Last Activity (O 17:10)
        ('2026-01-23 08:00:00', 'I'),
        ('2026-01-23 08:05:00', 'I'),
        ('2026-01-23 17:00:00', 'O'),
        ('2026-01-23 17:05:00', 'O'),
        ('2026-01-23 17:10:00', 'O'),
        
        # Day 3: Next Day Check-In (Should auto-close if anything was left open)
        ('2026-01-24 09:00:00', 'I'),
    ]

    new_logs = env['onedrive.attendance']
    for t, c_type in test_logs:
        l = env['onedrive.attendance'].create({
            'user_id': user_id,
            'check_time': t,
            'check_type': c_type,
            'sync_status': 'pending',
            'sensor_id': 'TEST_UNIFIED'
        })
        new_logs += l
    
    env.cr.commit()
    print(f"Created {len(new_logs)} logs.")

    print("Running Sync on Specific Logs...")
    # Pass records directly to sync
    env['onedrive.attendance'].action_sync_to_hr_attendance(specific_logs=new_logs)
    env.cr.commit()

    print("Verifying Results:")
    att_recs = env['hr.attendance'].search([('employee_id', '=', emp.id)], order='check_in')
    for att in att_recs:
        print(f"  {att.check_in} -> {att.check_out} ({att.worked_hours}h)")
else:
    print(f"User {user_id} not mapped to employee!")
