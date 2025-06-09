# This is the FINAL ENHANCED Python code with a simplified 1-to-1 (SO Line to PP) creation logic
import frappe
from frappe import _
from frappe.utils import flt
import math # math is no longer strictly needed but kept for general utility

@frappe.whitelist()
def create_production_plans_from_so(sales_order_name):
    try:
        so_doc = frappe.get_doc("Sales Order", sales_order_name)
        
        # --- Prerequisite 1: Check for duplicate Production Plans ---
        existing_pps = frappe.db.exists(
            "Production Plan Sales Order", {"sales_order": sales_order_name}
        )
        if existing_pps:
            frappe.throw(_("Production Plans have already been created for this Sales Order."))

        # =========================================================================
        # === MODIFICATION START: Simplified pre-flight check for all Items ===
        # =========================================================================
        items_to_process = []
        items_without_bom = []

        for item in so_doc.items:
            # We only need to validate that a default BOM exists.
            default_bom_name = frappe.db.get_value(
                "BOM", {"item": item.item_code, "is_active": 1, "is_default": 1}, "name"
            )

            # A. Validate BOM exists
            if not default_bom_name:
                items_without_bom.append(item.item_code)
            else:
                # If validation passes, add the item to our processing list.
                # The 'custom_masterpack' is no longer needed here.
                items_to_process.append({
                    "item_code": item.item_code,
                    "description": item.description,
                    "sales_order_item": item.name,
                    "qty": item.qty, # This is the total quantity for the line item
                    "bom_no": default_bom_name
                })
        
        # --- Report any validation errors and stop ---
        if items_without_bom:
            frappe.throw(_("The following items do not have an active, default BOM: {0}").format(", ".join(items_without_bom)))
        # =======================================================================
        # === MODIFICATION END ==================================================
        # =======================================================================

        # =========================================================================
        # === MODIFICATION START: Simplified Production Plan creation loop      ===
        # =========================================================================
        total_created_count = 0
        for item_data in items_to_process:
            # We no longer need any splitting logic here.
            # We will create one Production Plan for the full quantity of the SO item.
            
            # Create a simpler description now that we aren't splitting by parts.
            description = f"For {sales_order_name} / {item_data['item_code']}"
            
            # Call the helper function once for each item with its full quantity.
            _create_single_production_plan(
                so_doc=so_doc, 
                item_data=item_data, 
                planned_qty=item_data["qty"], # Use the full quantity from the SO
                description=description
            )
            
            total_created_count += 1
        # =======================================================================
        # === MODIFICATION END ==================================================
        # =======================================================================
                
        frappe.db.commit()
        return _("{0} Production Plans created successfully").format(total_created_count)

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Production Plan Creation from SO Failed")
        frappe.throw(str(e))


def _create_single_production_plan(so_doc, item_data, planned_qty, description):
    """
    Helper function to create and process a single Production Plan document.
    This function remains unchanged as it's perfectly reusable.
    """
    pp = frappe.new_doc("Production Plan")
    
    # --- Set main fields ---
    pp.get_items_from = "Sales Order"
    pp.for_warehouse = "Work in Progress - L" 
    pp.company = so_doc.company
    pp.include_non_stock_items = 0
    pp.custom_so_pp_desc = description 

    # --- Append child table data ---
    
    pp.append("sales_orders", {
        "sales_order": so_doc.name,
        "sales_order_date": so_doc.transaction_date,
        "customer": so_doc.customer,
        "grand_total": so_doc.grand_total
    })
    
    pp.append("po_items", {
        "item_code": item_data["item_code"],
        "bom_no": item_data["bom_no"],
        "planned_qty": planned_qty, # This will be the full quantity passed from the loop
        "warehouse": "Finished Goods - L",
        "description": item_data["description"],
        "sales_order": so_doc.name,
        "sales_order_item": item_data["sales_order_item"]
    })
    
    pp.insert(ignore_permissions=True)
    
    # --- Call function to get raw materials ---
    required_items_list = frappe.call(
        "erpnext.manufacturing.doctype.production_plan.production_plan.get_items_for_material_requests",
        doc=pp.as_dict(),
        warehouses=[{"warehouse": "Bodega Ingresos - L"}]
    )

    # --- Populate raw materials and save ---
    if required_items_list:
        pp_to_update = frappe.get_doc("Production Plan", pp.name)
        pp_to_update.mr_items = []
        for item_row in required_items_list:
            pp_to_update.append("mr_items", item_row)
        pp_to_update.save(ignore_permissions=True)
