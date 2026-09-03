import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core'
import { NgbModal, NgbPaginationModule } from '@ng-bootstrap/ng-bootstrap'
import { NgxBootstrapIconsModule } from 'ngx-bootstrap-icons'
import { Subject, first, takeUntil } from 'rxjs'
import { Group } from 'src/app/data/group'
import { User } from 'src/app/data/user'
import { IfPermissionsDirective } from 'src/app/directives/if-permissions.directive'
import {
  PermissionAction,
  PermissionType,
  PermissionsService,
} from 'src/app/services/permissions.service'
import { GroupService } from 'src/app/services/rest/group.service'
import { UserService } from 'src/app/services/rest/user.service'
import { SettingsService } from 'src/app/services/settings.service'
import { ToastService } from 'src/app/services/toast.service'
import { setLocationHref } from 'src/app/utils/navigation'
import { ConfirmDialogComponent } from '../../common/confirm-dialog/confirm-dialog.component'
import { EditDialogMode } from '../../common/edit-dialog/edit-dialog.component'
import { GroupEditDialogComponent } from '../../common/edit-dialog/group-edit-dialog/group-edit-dialog.component'
import { UserEditDialogComponent } from '../../common/edit-dialog/user-edit-dialog/user-edit-dialog.component'
import { PageHeaderComponent } from '../../common/page-header/page-header.component'
import { ComponentWithPermissions } from '../../with-permissions/with-permissions.component'

@Component({
  selector: 'pngx-users-groups',
  templateUrl: './users-groups.component.html',
  styleUrls: ['./users-groups.component.scss'],
  imports: [
    PageHeaderComponent,
    IfPermissionsDirective,
    NgbPaginationModule,
    NgxBootstrapIconsModule,
  ],
})
export class UsersAndGroupsComponent
  extends ComponentWithPermissions
  implements OnInit, OnDestroy
{
  private usersService = inject(UserService)
  private groupsService = inject(GroupService)
  private toastService = inject(ToastService)
  private modalService = inject(NgbModal)
  permissionsService = inject(PermissionsService)
  private settings = inject(SettingsService)

  readonly users = signal<User[]>(null)
  readonly userCount = signal(0)
  readonly userPage = signal(1)
  readonly userPageSize = 25
  readonly groups = signal<Group[]>(null)

  unsubscribeNotifier: Subject<any> = new Subject()

  public get canViewUsers(): boolean {
    return this.permissionsService.currentUserCan(
      PermissionAction.View,
      PermissionType.User
    )
  }

  public get canViewGroups(): boolean {
    return this.permissionsService.currentUserCan(
      PermissionAction.View,
      PermissionType.Group
    )
  }

  ngOnInit(): void {
    if (this.canViewUsers) {
      this.loadUsers()
    }

    if (this.canViewGroups) {
      this.groupsService
        .listAll(null, null, { full_perms: true })
        .pipe(first(), takeUntil(this.unsubscribeNotifier))
        .subscribe({
          next: (r) => {
            this.groups.set(r.results)
          },
          error: (e) => {
            this.toastService.showError($localize`Error retrieving groups`, e)
          },
        })
    }
  }

  ngOnDestroy() {
    this.unsubscribeNotifier.next(true)
  }

  loadUsers() {
    this.usersService
      .list(this.userPage(), this.userPageSize, 'username', false, {
        full_perms: true,
      })
      .pipe(first(), takeUntil(this.unsubscribeNotifier))
      .subscribe({
        next: (r) => {
          this.users.set(r.results)
          this.userCount.set(r.count)
        },
        error: (e) => {
          this.toastService.showError($localize`Error retrieving users`, e)
        },
      })
  }

  editUser(user: User = null) {
    var modal = this.modalService.open(UserEditDialogComponent, {
      backdrop: 'static',
      size: 'xl',
    })
    modal.componentInstance.dialogMode.set(
      user ? EditDialogMode.EDIT : EditDialogMode.CREATE
    )
    modal.componentInstance.object = user
    modal.componentInstance.succeeded
      .pipe(takeUntil(this.unsubscribeNotifier))
      .subscribe((newUser: User) => {
        if (
          newUser.id === this.settings.currentUser().id &&
          (modal.componentInstance as UserEditDialogComponent).passwordIsSet
        ) {
          this.toastService.showInfo(
            $localize`Password has been changed, you will be logged out momentarily.`
          )
          setTimeout(() => {
            setLocationHref(
              `${window.location.origin}/accounts/logout/?next=/accounts/login/?next=/`
            )
          }, 2500)
        } else {
          this.toastService.showInfo(
            $localize`Saved user "${newUser.username}".`
          )
          this.loadUsers()
        }
      })
    modal.componentInstance.failed
      .pipe(takeUntil(this.unsubscribeNotifier))
      .subscribe((e) => {
        this.toastService.showError($localize`Error saving user.`, e)
      })
  }

  deleteUser(user: User) {
    let modal = this.modalService.open(ConfirmDialogComponent, {
      backdrop: 'static',
    })
    modal.componentInstance.title = $localize`Confirm delete user account`
    modal.componentInstance.messageBold = $localize`This operation will permanently delete this user account.`
    modal.componentInstance.message = $localize`This operation cannot be undone.`
    modal.componentInstance.btnClass = 'btn-danger'
    modal.componentInstance.btnCaption = $localize`Proceed`
    modal.componentInstance.confirmClicked.subscribe(() => {
      modal.componentInstance.buttonsEnabled.set(false)
      this.usersService.delete(user).subscribe({
        next: () => {
          modal.close()
          this.toastService.showInfo($localize`Deleted user "${user.username}"`)
          if (this.users().length === 1 && this.userPage() > 1) {
            this.userPage.update((page) => page - 1)
          }
          this.loadUsers()
        },
        error: (e) => {
          this.toastService.showError(
            $localize`Error deleting user "${user.username}".`,
            e
          )
        },
      })
    })
  }

  editGroup(group: Group = null) {
    var modal = this.modalService.open(GroupEditDialogComponent, {
      backdrop: 'static',
      size: 'lg',
    })
    modal.componentInstance.dialogMode.set(
      group ? EditDialogMode.EDIT : EditDialogMode.CREATE
    )
    modal.componentInstance.object = group
    modal.componentInstance.succeeded
      .pipe(takeUntil(this.unsubscribeNotifier))
      .subscribe((newGroup) => {
        this.toastService.showInfo($localize`Saved group "${newGroup.name}".`)
        this.groupsService.listAll().subscribe((r) => {
          this.groups.set(r.results)
        })
      })
    modal.componentInstance.failed
      .pipe(takeUntil(this.unsubscribeNotifier))
      .subscribe((e) => {
        this.toastService.showError($localize`Error saving group.`, e)
      })
  }

  deleteGroup(group: Group) {
    let modal = this.modalService.open(ConfirmDialogComponent, {
      backdrop: 'static',
    })
    modal.componentInstance.title = $localize`Confirm delete user group`
    modal.componentInstance.messageBold = $localize`This operation will permanently delete this user group.`
    modal.componentInstance.message = $localize`This operation cannot be undone.`
    modal.componentInstance.btnClass = 'btn-danger'
    modal.componentInstance.btnCaption = $localize`Proceed`
    modal.componentInstance.confirmClicked.subscribe(() => {
      modal.componentInstance.buttonsEnabled.set(false)
      this.groupsService.delete(group).subscribe({
        next: () => {
          modal.close()
          this.toastService.showInfo($localize`Deleted group "${group.name}"`)
          this.groupsService.listAll().subscribe((r) => {
            this.groups.set(r.results)
          })
        },
        error: (e) => {
          this.toastService.showError(
            $localize`Error deleting group "${group.name}".`,
            e
          )
        },
      })
    })
  }

  getGroupName(id: number): string {
    return this.groups()?.find((g) => g.id === id)?.name ?? ''
  }
}
